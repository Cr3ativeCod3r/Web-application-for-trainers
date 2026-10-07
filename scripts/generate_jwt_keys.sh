#!/usr/bin/env sh
# Generates the ES256 key pair used for chat tokens:
#   jwt_private.pem - main app only (signs tokens)
#   jwt_public.pem  - chat service (verifies tokens)
# Usage: ./scripts/generate_jwt_keys.sh [output-dir]   (default: ./secrets)
set -eu

out="${1:-secrets}"
mkdir -p "$out"

if [ -e "$out/jwt_private.pem" ]; then
  echo "$out/jwt_private.pem already exists - refusing to overwrite it." >&2
  exit 1
fi

openssl ecparam -name prime256v1 -genkey -noout | openssl pkcs8 -topk8 -nocrypt -out "$out/jwt_private.pem"
openssl ec -in "$out/jwt_private.pem" -pubout -out "$out/jwt_public.pem" 2>/dev/null
chmod 600 "$out/jwt_private.pem"
echo "Keys written to $out/"
