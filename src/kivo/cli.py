import argparse
import sys
import os
import uvicorn
from kivo.engine import KivoEngine

def print_banner():
    print("""
 ██╗  ██╗██╗██╗   ██╗ ██████╗ 
 ██║ ██╔╝██║██║   ██║██╔═══██╗
 █████╔╝ ██║██║   ██║██║   ██║
 ██╔═██╗ ██║╚██╗ ██╔╝██║   ██║
 ██║  ██╗██║ ╚████╔╝ ╚██████╔╝
 ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═════╝ 
  Semantic Layer CLI v0.1.0
""")

def handle_server_start(args):
    """Starts the Kivo Semantic FastAPI server."""
    host = args.host
    port = args.port
    reload = args.reload
    models_dir = args.models_dir
    
    # Configure environments
    os.environ["KIVO_MODELS_DIR"] = models_dir
    if args.db_type:
        os.environ["KIVO_DATABASE_TYPE"] = args.db_type
    
    print_banner()
    print(f"Starting Kivo API Server on http://{host}:{port}")
    print(f"Loading semantic models from directory: '{models_dir}'")
    print(f"Database type configured: '{os.getenv('KIVO_DATABASE_TYPE', 'duckdb')}'")
    print("-" * 50)
    
    uvicorn.run("kivo.server:app", host=host, port=port, reload=reload)

def handle_compile(args):
    """Compiles a query directly from the CLI and prints raw SQL."""
    models_dir = args.models_dir
    model_name = args.model
    dimensions = [d.strip() for d in args.dimensions.split(",") if d.strip()] if args.dimensions else []
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()] if args.metrics else []
    filters = [f.strip() for f in args.filters.split(",") if f.strip()] if args.filters else []
    dialect = args.dialect
    
    if not os.path.exists(models_dir):
        print(f"[ERROR] Models directory '{models_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    engine = KivoEngine()
    engine.load_models(models_dir)
    
    try:
        sql = engine.compile(
            model_name=model_name,
            dimensions=dimensions,
            metrics=metrics,
            filters=filters,
            dialect=dialect
        )
        print("\n--- Compiled SQL Query ---")
        print(sql)
        print("-" * 26)
    except Exception as e:
        print(f"[ERROR] Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Kivo Semantic Layer CLI tool.")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # Subcommand: server
    server_parser = subparsers.add_parser("server", help="Manage the Kivo API server")
    server_subparsers = server_parser.add_subparsers(dest="server_command", help="Server commands")
    
    start_parser = server_subparsers.add_parser("start", help="Start the Kivo API server")
    start_parser.add_argument("--host", default="127.0.0.1", help="Host address to bind server (default: 127.0.0.1)")
    start_parser.add_argument("--port", type=int, default=8000, help="Port to run server (default: 8000)")
    start_parser.add_argument("--reload", action="store_true", help="Enable automatic hot reload on source change")
    start_parser.add_argument("--models-dir", default="models", help="Directory containing semantic YAML models (default: models)")
    start_parser.add_argument("--db-type", choices=["duckdb", "postgres", "clickhouse", "bigquery"], help="Target database executor type")
    
    # Subcommand: compile
    compile_parser = subparsers.add_parser("compile", help="Compile a semantic query directly to SQL")
    compile_parser.add_argument("--model", required=True, help="Semantic model name to query")
    compile_parser.add_argument("--dimensions", required=True, help="Comma-separated dimension names")
    compile_parser.add_argument("--metrics", required=True, help="Comma-separated metric names")
    compile_parser.add_argument("--filters", help="Comma-separated query-level filter expressions")
    compile_parser.add_argument("--dialect", help="Output SQL target dialect (e.g., postgres, clickhouse, duckdb, bigquery)")
    compile_parser.add_argument("--models-dir", default="models", help="Directory containing semantic YAML models (default: models)")
    
    # Subcommand: version
    subparsers.add_parser("version", help="Print version info")
    
    args = parser.parse_args()
    
    if args.command == "server" and args.server_command == "start":
        handle_server_start(args)
    elif args.command == "compile":
        handle_compile(args)
    elif args.command == "version":
        print("Kivo Semantic Layer CLI v0.1.0")
    else:
        parser.print_help()
        sys.exit(0)

if __name__ == "__main__":
    main()
