
if which npx > /dev/null 2>&1
then
    npx auto-changelog -p --sort-commits date --starting-version 0.15.0
else
    echo ERROR: Update changelog failed.
    echo npx not available on your system. Install nodejs -> https://nodejs.org/en/download/
fi
