# Parsers of the Romanian ParlaMint corpus files #

## Processing pipeline ##

1. Run `python crawl-deputy-data.py` to download corpus metadata (list of deputies with their affiliations)
2. The metadata of the corpus should be inspected by human experts to assert and correct the data
3. Run `python parse-sessions.py` to create TEI corpus files using:
   1. `./corpus` - directory where the HTML transcriptions are located
   2. `session-template.xml` - template file on which every corpus file is based
   3. `./output` - directory where the TEI corpus files will be saved.
4. Run `python build-corpus-root.py` to build the corpus root file using:
   1. `./output` - directory containing individual TEI corpus files
   2. `deputy-affiliations.csv` - the file containing corpus metadata, after it was inspected and corrected by the human experts.
5. Remove duplicate entries in `listPerson` element and fix any other errors manually. This is required because some of the speakers are missing data and it's easier to just apply the fixes by hand.
