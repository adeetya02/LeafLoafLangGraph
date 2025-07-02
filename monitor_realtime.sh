#!/bin/bash
# Real-time voice monitoring script

echo "🎙️ LeafLoaf Voice Monitor - Real-time"
echo "===================================="
echo "Monitoring voice interactions..."
echo ""

tail -f server.log | grep -E "(🎙️|🎤|💬|✅|❌|🔍|Voice-native|intent|urgency|pace|emotion|mood|Gemma|alpha|confidence|products found|Transcript|Response|Search|trace_id)" --line-buffered | while read line; do
    # Color important lines
    if [[ $line == *"Voice-native"* ]]; then
        echo -e "\033[1;36m$line\033[0m"  # Cyan for voice analysis
    elif [[ $line == *"Gemma 2 analysis"* ]]; then
        echo -e "\033[1;35m$line\033[0m"  # Magenta for Gemma analysis
    elif [[ $line == *"Transcript received"* ]]; then
        echo -e "\033[1;32m$line\033[0m"  # Green for transcripts
    elif [[ $line == *"Response sent"* ]]; then
        echo -e "\033[1;33m$line\033[0m"  # Yellow for responses
    elif [[ $line == *"error"* ]]; then
        echo -e "\033[1;31m$line\033[0m"  # Red for errors
    else
        echo "$line"
    fi
done