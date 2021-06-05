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
6. Manually build the annotated corpus root skeleton:
   - Copy the corpus root file (`ParlaMint-RO.xml`) to annotated root file (`ParlaMint-RO.ana.xml`)
   - Open the annotated root file
   - Add the taxonomy for `UD-SYN` terms:

            <taxonomy xml:id="UD-SYN">
              <desc xml:lang="en">
                <term>UD syntactic relations</term>
              </desc>
              <desc xml:lang="ro">
                <term>Rela&#x21B;ii sintactice UD.</term>
              </desc>
              <category xml:id="acl">
                <catDesc xml:lang="en"><term>acl</term>: Clausal modifier of noun (adjectival clause)</catDesc>
              </category>
              <category xml:id="acl_relcl">
                <catDesc xml:lang="en"><term>acl:relcl</term>: relative clause modifier</catDesc>
              </category>
              <category xml:id="advcl">
                <catDesc xml:lang="en"><term>advcl</term>: Adverbial clause modifier</catDesc>
              </category>
              <category xml:id="advmod">
                <catDesc xml:lang="en"><term>advmod</term>: Adverbial modifier</catDesc>
              </category>
              <category xml:id="amod">
                <catDesc xml:lang="en"><term>amod</term>: Adjectival modifier</catDesc>
              </category>
              <category xml:id="appos">
                <catDesc xml:lang="en"><term>appos</term>: Appositional modifier</catDesc>
              </category>
              <category xml:id="aux">
                <catDesc xml:lang="en"><term>aux</term>: Auxiliary</catDesc>
              </category>
              <category xml:id="aux_pass">
                <catDesc xml:lang="en"><term>aux:pass</term>: passive auxiliary</catDesc>
              </category>
              <category xml:id="case">
                <catDesc xml:lang="en"><term>case</term>: Case marking</catDesc>
              </category>
              <category xml:id="cc">
                <catDesc xml:lang="en"><term>cc</term>: Coordinating conjunction</catDesc>
              </category>
              <category xml:id="ccomp">
                <catDesc xml:lang="en"><term>ccomp</term>: Clausal complement</catDesc>
              </category>
              <category xml:id="compound">
                <catDesc xml:lang="en"><term>compound</term>: compound</catDesc>
              </category>
              <category xml:id="conj">
                <catDesc xml:lang="en"><term>conj</term>: Conjunct</catDesc>
              </category>
              <category xml:id="cop">
                <catDesc xml:lang="en"><term>cop</term>: Copula</catDesc>
              </category>
              <category xml:id="csubj">
                <catDesc xml:lang="en"><term>csubj</term>: Clausal subject</catDesc>
              </category>
              <category xml:id="csubj_pass">
                <catDesc xml:lang="en"><term>csubj:pass</term>: Clausal passive subject</catDesc>
              </category>
              <category xml:id="dep">
                <catDesc xml:lang="en"><term>dep</term>: Unspecified dependency</catDesc>
              </category>
              <category xml:id="det">
                <catDesc xml:lang="en"><term>det</term>: Determiner</catDesc>
              </category>
              <category xml:id="det_poss">
                <catDesc xml:lang="en"><term>det:poss</term>: possessive determiner</catDesc>
              </category>
              <category xml:id="det_predet">
                <catDesc xml:lang="en"><term>det:predet</term>: predeterminer</catDesc>
              </category>
              <category xml:id="discourse">
                <catDesc xml:lang="en"><term>discourse</term>: Discourse element</catDesc>
              </category>
              <category xml:id="discourse_emo">
                <catDesc xml:lang="en"><term>discourse:emo</term>: emoticons, emojis</catDesc>
              </category>
              <category xml:id="dislocated">
                <catDesc xml:lang="en"><term>dislocated</term>: Dislocated elements</catDesc>
              </category>
              <category xml:id="expl">
                <catDesc xml:lang="en"><term>expl</term>: Expletive</catDesc>
              </category>
              <category xml:id="expl_impers">
                <catDesc xml:lang="en"><term>expl:impers</term>: impersonal expletive</catDesc>
              </category>
              <category xml:id="expl_pass">
                <catDesc xml:lang="en"><term>expl:pass</term>: reflexive pronoun used in reflexive passive</catDesc>
              </category>
              <category xml:id="fixed">
                <catDesc xml:lang="en"><term>fixed</term>: Fixed multiword expression</catDesc>
              </category>
              <category xml:id="flat">
                <catDesc xml:lang="en"><term>flat</term>: Flat multiword expression</catDesc>
              </category>
              <category xml:id="flat_foreign">
                <catDesc xml:lang="en"><term>flat:foreign</term>: Flat multiword expression: foreign</catDesc>
              </category>
              <category xml:id="flat_name">
                <catDesc xml:lang="en"><term>flat:name</term>: Flat name</catDesc>
              </category>
              <category xml:id="goeswith">
                <catDesc xml:lang="en"><term>goeswith</term>: goeswith</catDesc>
              </category>
              <category xml:id="iobj">
                <catDesc xml:lang="en"><term>iobj</term>: Indirect object</catDesc>
              </category>
              <category xml:id="list">
                <catDesc xml:lang="en"><term>list</term>: List</catDesc>
              </category>
              <category xml:id="mark">
                <catDesc xml:lang="en"><term>mark</term>: Marker</catDesc>
              </category>
              <category xml:id="nmod">
                <catDesc xml:lang="en"><term>nmod</term>: Nominal modifier</catDesc>
              </category>
              <category xml:id="nsubj">
                <catDesc xml:lang="en"><term>nsubj</term>: Nominal subject</catDesc>
              </category>
              <category xml:id="nsubj_pass">
                <catDesc xml:lang="en"><term>nsubj:pass</term>: passive nominal subject</catDesc>
              </category>
              <category xml:id="nummod">
                <catDesc xml:lang="en"><term>nummod</term>: Numeric modifier</catDesc>
              </category>
              <category xml:id="obj">
                <catDesc xml:lang="en"><term>obj</term>: Object</catDesc>
              </category>
              <category xml:id="obl">
                <catDesc xml:lang="en"><term>obl</term>: Oblique nominal</catDesc>
              </category>
              <category xml:id="obl_agent">
                <catDesc xml:lang="en"><term>obl:agent</term>: agent modifier</catDesc>
              </category>
              <category xml:id="orphan">
                <catDesc xml:lang="en"><term>orphan</term>: orphan-to-orphan relation in gapping</catDesc>
              </category>
              <category xml:id="parataxis">
                <catDesc xml:lang="en"><term>parataxis</term>: Parataxis</catDesc>
              </category>
              <category xml:id="parataxis_appos">
                <catDesc xml:lang="en"><term>parataxis:appos</term>: paratactic apposition</catDesc>
              </category>
              <category xml:id="parataxis_discourse">
                <catDesc xml:lang="en"><term>parataxis:discourse</term>: paratactic discourse</catDesc>
              </category>
              <category xml:id="parataxis_hashtag">
                <catDesc xml:lang="en"><term>parataxis:hashtag</term>: paratactic hashtag</catDesc>
              </category>
              <category xml:id="parataxis_insert">
                <catDesc xml:lang="en"><term>parataxis:insert</term>: paratactic insert</catDesc>
              </category>
              <category xml:id="parataxis_nsubj">
                <catDesc xml:lang="en"><term>parataxis:nsubj</term>: paratactic nominal subject</catDesc>
              </category>
              <category xml:id="parataxis_obj">
                <catDesc xml:lang="en"><term>parataxis:obj</term>: direct speech</catDesc>
              </category>
              <category xml:id="punct">
                <catDesc xml:lang="en"><term>punct</term>: Punctuation</catDesc>
              </category>
              <category xml:id="reparandum">
                <catDesc xml:lang="en"><term>reparandum</term>: Overridden disfluency (here used for program mistakes!)</catDesc>
              </category>
              <category xml:id="root">
                <catDesc xml:lang="en"><term>root</term>: Root</catDesc>
              </category>
              <category xml:id="vocative">
                <catDesc xml:lang="en"><term>vocative</term>: Vocative</catDesc>
              </category>
              <category xml:id="vocative_mention">
                <catDesc xml:lang="en"><term>vocative:mention</term>: Vocative mention</catDesc>
              </category>
              <category xml:id="xcomp">
                <catDesc xml:lang="en"><term>xcomp</term>: Open clausal complement</catDesc>
              </category>
            </taxonomy>


   - Add `listPrefixDef` and `appInfo` elements _after_ `classDecl`:

            <listPrefixDef>
              <prefixDef ident="ud-syn" matchPattern="(.+)" replacementPattern="#$1">
                <p xml:lang="ro">URI-urile cu acest prefix indică numele elementelor. În acest document aceste URI-uri fac referință la categoriile din taxonomia UD-SYN.</p>
                <p xml:lang="en">Private URIs with this prefix point to elements giving their name. In this document they are simply local references into the UD-SYN taxonomy categories in the corpus root TEI header.</p>
              </prefixDef>
            </listPrefixDef>
            <appInfo>
              <application version="2" ident="app-udpipe">
                <label>UDPipe</label>
                <desc xml:lang="en"><ref target="http://lindat.mff.cuni.cz/services/udpipe/info.php">UDPipe</ref>: a trainable pipeline for tokenization, tagging, lemmatization, and dependency parsing of CoNLL-U files. Pretrained model based on the <ref target="https://universaldependencies.org/treebanks/ro_rrt/index.html">UD Romanian RRT</ref> treebank, version 2.6.</desc>
              </application>
              <application version="1" ident="app-roparl-analyzer">
                <label>Romanian ParlaMint lexical analysis pipeline</label>
                <desc xml:lang="en"><ref target="https://github.com/romanian-parlamint/parsers/blob/main/apply-linguistic-annotation.py">Lexical analysis pipeline</ref> which applies UDPipe processing to each segment and saves the data into TEI XML format.</desc>
              </application>
            </appInfo>

   - Remove `<xsi:include>` elements
   - Save the file
7. Run `python apply-linguistic-annotation.py` to perform linguistic annotations on the corpus.
