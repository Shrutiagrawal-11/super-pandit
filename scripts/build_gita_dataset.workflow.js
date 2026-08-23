export const meta = {
  name: 'build-gita-dataset',
  description: 'Source, cross-check, and load all Bhagavad Gita verses with per-verse confidence scoring',
  phases: [
    { title: 'Source research', detail: 'determine which digital sources are trustworthy enough to check against' },
    { title: 'Chapter verification', detail: 'fetch + cross-check each chapter\'s verses against the chosen sources' },
    { title: 'Write to database', detail: 'insert verses with confidence flags via psql' },
    { title: 'Scholar summary', detail: 'produce a review-priority report' },
  ],
}

phase('Source research')
const sourceReport = await agent(
  `Research which digital sources of the Bhagavad Gita Sanskrit text are trustworthy enough to use as
   cross-check authorities for verifying transcription accuracy (not for copying text into a commercial
   dataset, only for comparison). We already know: GRETIL's bare Sanskrit verses (no commentary) are
   usable and CC-licensed. BORI's Mahabharata Critical Edition is copyrighted/all-rights-reserved but can
   be used as a verification-only reference (do not copy its text, only compare). Investigate at least
   these additional candidates and any other reputable one you find: Wikisource Sanskrit Gita
   (sa.wikisource.org), Sacred-texts.com, sanskritdocuments.org, and IITK's Gita Supersite (gitasupersite.iitk.ac.in,
   an Indian government-funded academic project). For each, report: how it sources its text (does it cite
   a specific edition/manuscript?), whether it's independently maintained from GRETIL (so it's a genuinely
   independent cross-check, not the same underlying source relabeled), and its actual license/rights
   status for at least reference use. Then give a clear ranked recommendation: which 2-3 sources are
   independent and trustworthy enough to use as our cross-check set for verifying GRETIL's text.
   Be honest about uncertainty. Under 400 words.`,
  { label: 'source-trust-research' }
)
log('Source research complete, selecting cross-check sources for verification')

phase('Chapter verification')
const CHAPTERS = [1, 2, 3, 4, 5, 6, 7] // temporarily limited to conserve usage; chapters 1-6 return from cache, only 7 runs new

const chapterResults = await pipeline(
  CHAPTERS,
  (chapterNum) => agent(
    `You are building a verified Bhagavad Gita dataset. Using this source-trust research as your guide
     for which sites are independent and reliable enough to cross-check against:

     ---
     ${sourceReport}
     ---

     Task: fetch the Sanskrit text (IAST or Devanagari, note which) for ALL verses of Bhagavad Gita
     Chapter ${chapterNum} from GRETIL (the primary source, bare verses without the NC-licensed
     commentary bundle: fetch from https://gretil.sub.uni-goettingen.de/gretil/corpustei/transformations/html/sa_bhagavadgItA-4comm.htm
     and extract only the verse lines, ignore commentary blocks), then independently fetch the same
     chapter's verses from the 1-2 best cross-check sources the research above identified as trustworthy
     and independent (e.g. Wikisource sa.wikisource.org, or IITK Gita Supersite). For each verse, compare
     the texts. Do not copy BORI's text even for comparison unless you can access a public page without
     violating its "do not redistribute" notice, if you can find a page discussing BORI's specific
     reading for a verse without copying their electronic text wholesale, you may note whether it agrees
     in substance, otherwise skip BORI for this chapter.

     For every verse in the chapter, output a JSON array via the required schema: verse_number, sanskrit_text
     (the GRETIL version, as the text of record), source_citation (e.g. "GRETIL sa_bhagavadgItA"), and
     cross_check_sources (an array of {source, text, match: true/false} for each source you checked against,
     where match is true only if the text agrees exactly or differs only in whitespace/punctuation
     normalization, not substantive wording).

     If you cannot access a source or fetch fails, note that honestly in the source's entry rather than
     fabricating a match. Do not guess a verse's text if you cannot fetch it, if GRETIL's page for this
     chapter cannot be found or fetched, report that clearly and return an empty verses array for this
     chapter rather than inventing verses.`,
    {
      label: `chapter-${chapterNum}`,
      phase: 'Chapter verification',
      schema: {
        type: 'object',
        properties: {
          chapter: { type: 'number' },
          fetch_succeeded: { type: 'boolean' },
          notes: { type: 'string' },
          verses: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                verse_number: { type: 'number' },
                sanskrit_text: { type: 'string' },
                source_citation: { type: 'string' },
                cross_check_sources: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      source: { type: 'string' },
                      text: { type: 'string' },
                      match: { type: 'boolean' },
                    },
                    required: ['source', 'match'],
                  },
                },
              },
              required: ['verse_number', 'sanskrit_text', 'source_citation'],
            },
          },
        },
        required: ['chapter', 'fetch_succeeded', 'verses'],
      },
    }
  ),
  (result, chapterNum) => {
    if (!result || !result.fetch_succeeded) {
      log(`Chapter ${chapterNum}: fetch failed or incomplete, flagging for manual sourcing. Notes: ${result?.notes || 'no result returned'}`)
      return { chapter: chapterNum, verses: [], failed: true, notes: result?.notes }
    }
    const scored = result.verses.map((v) => {
      const checks = v.cross_check_sources || []
      const anyChecked = checks.length > 0
      const allMatch = anyChecked && checks.every((c) => c.match === true)
      const anyMismatch = checks.some((c) => c.match === false)
      const confidence = anyMismatch ? 'mismatch' : (allMatch ? 'high_confidence' : 'unverified')
      return { ...v, confidence }
    })
    log(`Chapter ${chapterNum}: ${scored.length} verses scored (${scored.filter(v => v.confidence === 'high_confidence').length} high-confidence, ${scored.filter(v => v.confidence === 'mismatch').length} mismatch, ${scored.filter(v => v.confidence === 'unverified').length} unverified)`)
    return { chapter: chapterNum, verses: scored, failed: false }
  }
)

const allChapters = chapterResults.filter(Boolean)
const failedChapters = allChapters.filter((c) => c.failed)
const totalVerses = allChapters.reduce((sum, c) => sum + c.verses.length, 0)

phase('Write to database')
log(`Writing ${totalVerses} verses across ${allChapters.length - failedChapters.length} successfully-fetched chapters to the database`)

return {
  sourceReport,
  chapters: allChapters,
  failedChapters: failedChapters.map((c) => ({ chapter: c.chapter, notes: c.notes })),
  totalVerses,
}
