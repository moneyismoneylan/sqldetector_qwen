from typing import Dict, List

TIPS: Dict[str, str] = {
    "django": "Use Django ORM parameterisation: MyModel.objects.raw(\"SELECT ... WHERE id=%s\", [id])",
    "laravel": "Use Laravel query builder parameter binding: DB::select('SELECT ... WHERE id = ?', [id])",
    "dotnet": "Use SqlParameter with parameterised queries to avoid string concatenation.",
}


def remediation_for(stack: str) -> List[str]:
    tip = TIPS.get(stack.lower())
    return [tip] if tip else []
