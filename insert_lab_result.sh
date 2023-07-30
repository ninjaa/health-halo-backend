#!/bin/bash

# This is your script to call the CURL command and display its output.

curl 'http://localhost:8000/conduct_chat' \
    -H 'Content-Type: application/json' \
    --data-raw '{
    "initial_messages": [{"role": "user", "lab_result": "A new value has just been reported for Calcium at 12. Review the patient record and SMS the care team with the clinical significance of the new record" }]
}' \
    --compressed

echo "Command executed!"

