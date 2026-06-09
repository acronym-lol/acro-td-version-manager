#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
launchctl setenv ACRO_TD_VERSION_MANAGER "$SCRIPT_DIR"
if ! grep -q 'ACRO_TD_VERSION_MANAGER' ~/.zshenv 2>/dev/null; then
    echo "export ACRO_TD_VERSION_MANAGER=\"$SCRIPT_DIR\"" >> ~/.zshenv
fi
export ACRO_TD_VERSION_MANAGER="$SCRIPT_DIR"
echo "ACRO_TD_VERSION_MANAGER set to $SCRIPT_DIR"
