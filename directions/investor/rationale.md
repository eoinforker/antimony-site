# Investor direction: rationale

A partner opens this on a phone between meetings. They give it ten seconds and leave with one impression. Every decision below serves that impression: a serious company, clear about what it makes, with taste and ambition it does not need to announce.

## What is on the page

One image, one name, one sentence, three products. Nothing else.

- **The image.** The Break, Antimony's mark, as a stone monolith standing in a still lake at first light, rendered in Blender (Cycles). The mark's geometry is exact: the 22 radius tile, the seam at 16 degrees, the cavity and the crystal. A small figure stands on a spit of shingle in the shallows, for scale.
- **The wordmark**, the drawn lowercase antimony with its crystal tittle.
- **One sentence:** "Antimony is a software company in London that builds for the people who make the work." Every word of it comes from material Antimony already publishes. There are no numbers, no customers, no investors and no partners, because none are stated anywhere.
- **The three products**, each a plain link with the one line description and stage the live home page already gives them: Orbe (Live), immiscible (Alpha), Idyll (Soon).
- No contact route, because none exists in the materials. An invented address would be worse than none.

## Why each decision earns respect

- **Clarity first.** Name, sentence and products all read before the image does any work. An investor should never have to work out what the company is.
- **Stage stated honestly.** Live, Alpha and Soon tell an investor more than any adjective. Saying "Soon" next to Idyll is a sign of confidence, not weakness.
- **Scale without hype.** A vast, quiet place and a monolith many times a person's height carry ambition without a single claim. The image does the boasting so the copy does not have to.
- **Restraint.** No scroll, no sections, no carousel, no animation that asks for attention. The best holding company and lab pages say less than they could; so does this one.
- **Craft that is felt rather than shown.** A path traced image, real typography in the house face, kerning, a type size that holds on a phone, and a single quiet interaction: the crystal catches the light as the pointer moves.
- **Speed is part of the impression.** A tiny blurred placeholder paints with the HTML, the still replaces it, and only then does the loop load, and never on a saved data plan or under reduced motion. A slow page reads as a slow company.
- **Nothing reads as a demo.** No WebGL on load, no loader, no intro that has to finish before you can read. The arrival is a single fade of the words, once a session, and any gesture skips it.
- **Accessible by default.** Real text, a semantic heading and list, visible focus, contrast held by a gentle grade under the words rather than a box, and a still frame for reduced motion. Sound is off until asked for.

## What it costs to load

On a phone the first view is about 64 KB: the page with its inline placeholder (23 KB), the portrait still (12 KB AVIF), the type (17 KB), the grain and the crystal mask. The 8 second loop (53 KB WebM, 168 KB MP4) only loads after the still has painted. On a throttled mobile connection in testing, first paint came at about 0.3 seconds.

## What to test with real investors

1. **The ten second read.** Show the page on a phone for ten seconds, take it away, ask: what does this company do, and what is its first product? If they cannot say "software for creators" and "Orbe", the sentence needs work, not the image.
2. **The monolith.** Ask what the image says about the company. Listen for "serious", "ambitious", "calm". If anyone says "app icon", "screensaver" or "game", the render needs more atmosphere or a wider frame.
3. **Live, Alpha, Soon.** Do the stage labels raise trust or invite doubt? Try the page with and without them.
4. **The sentence.** Test it against a sharper version that names the customer ("for creators") once that wording is confirmed by the founder. Investors reward specificity.
5. **Contact.** Ask whether the absence of a way to get in touch feels confident or careless. If careless, add one real address, nothing more.
6. **Speed on a real phone, on mobile data.** Time to the first readable words and to the full still.
