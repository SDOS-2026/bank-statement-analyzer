#!/usr/bin/env bash
echo "Stopping FinParse services…"
pkill -f "python.*app.py"    2>/dev/null && echo "  ✓ Python parser stopped"  || echo "  – Python parser was not running"
pkill -f "bank-parser-backend" 2>/dev/null && echo "  ✓ Spring Boot stopped"  || echo "  – Spring Boot was not running"
pkill -f "ng serve"          2>/dev/null && echo "  ✓ Angular stopped"        || echo "  – Angular was not running"
echo "Done."
