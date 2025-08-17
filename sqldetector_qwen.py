import argparse
from sqldetector.planner import pipeline

def main(argv=None):
    parser = argparse.ArgumentParser(description="AI-powered SQL injection detector")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without network calls")
    args = parser.parse_args(argv)
    return pipeline.run(args.url, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
