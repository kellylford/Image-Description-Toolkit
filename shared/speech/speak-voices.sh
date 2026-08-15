#!/usr/bin/env bash
# ClaudeSpeak probe (macOS). Reports what speech routes and voices this machine
# actually has, as JSON. Read-only — changes nothing.
#
#   speak-voices.sh          en_* voices only (there are usually 400+ in total)
#   speak-voices.sh --all    every installed voice
set -uo pipefail

all=false
[ "${1:-}" = "--all" ] && all=true

vo_installed=false
[ -d /System/Library/CoreServices/VoiceOver.app ] && vo_installed=true

vo_running=false
pgrep -f 'VoiceOver.app/Contents/MacOS/VoiceOver' >/dev/null 2>&1 && vo_running=true

# Apple Events reaching VoiceOver is necessary but not sufficient: the "output"
# command stays silent when AppleScript control is switched off, and reports no
# error when it does. So this is "addressable", never "will definitely speak".
vo_addressable=false
if [ "$vo_running" = true ]; then
    /usr/bin/osascript -e 'tell application "VoiceOver" to get version' >/dev/null 2>&1 \
        && vo_addressable=true
fi

voice_json=$(
    /usr/bin/say -v '?' 2>/dev/null | while IFS= read -r line; do
        # "Name with spaces (and parens)   en_US    # Sample sentence."
        name=$(printf '%s' "$line" | sed -E 's/[[:space:]]{2,}[a-z]{2}_[A-Z]{2}[[:space:]]+#.*$//')
        locale=$(printf '%s' "$line" | sed -nE 's/.*[[:space:]]{2,}([a-z]{2}_[A-Z]{2})[[:space:]]+#.*/\1/p')
        [ -n "$name" ] && [ -n "$locale" ] || continue
        # Skip non-English unless --all: there are 400+ voices in total.
        if [ "$all" != true ] && [ "${locale#en_}" = "$locale" ]; then
            continue
        fi
        jq -nc --arg n "$name" --arg l "$locale" '{name:$n, locale:$l, match:$n}'
    done | jq -sc '.'
)
[ -n "$voice_json" ] || voice_json='[]'

jq -n \
    --arg os "$(sw_vers -productName) $(sw_vers -productVersion)" \
    --argjson voInstalled "$vo_installed" \
    --argjson voRunning "$vo_running" \
    --argjson voAddressable "$vo_addressable" \
    --argjson voices "$voice_json" \
    --argjson all "$all" \
'{
  platform: $os,
  screenReaders: [
    { name: "VoiceOver",
      engine: "voiceover",
      available: $voInstalled,
      running: $voRunning,
      addressable: $voAddressable }
  ],
  systemVoices: $voices,
  voiceListFiltered: ($all | not),
  rateRange: { say: { min: 90, max: 720, default: 175, units: "words per minute" } },
  notes: [
    "addressable only means Apple Events reach VoiceOver. The output command is silent, with no error, when \"Allow VoiceOver to be controlled with AppleScript\" is off in VoiceOver Utility > General. The only proof is listening.",
    "The voiceover route has no voice or rate setting, by design: it speaks in whatever voice, rate and punctuation level VoiceOver is already configured with, and follows automatically if the user changes those. The VoiceOver voice cannot be set from here and should not be, being a global setting. voice and rate below apply to the say route only.",
    "systemVoices are say voices. An empty voice in the config means the machine default Spoken Content voice, which is a reasonable answer rather than a missing one.",
    "Side effect of the above: Eloquence is a VoiceOver-only synthesiser on macOS, absent from say, so it is audible on the voiceover route and no other. Relevant only if the user asks for it by name.",
    (if ($all | not) then "Showing en_* voices only. Pass --all for every installed language." else "Showing every installed voice." end)
  ]
}'
