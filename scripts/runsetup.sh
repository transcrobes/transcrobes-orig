export PYTHONPATH=$PYTHONPATH:$APP_PATH

# execute dev workstation-specific init (like making sure the db is running, etc.)
# FIXME: find out how this is supposed to work but doesn't
# cd "${BASH_SOURCE%/*}"

FILE=.local_setup.sh
if [ -f "$FILE" ]; then
    source $FILE
fi
