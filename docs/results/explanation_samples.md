# Explanation samples (for manual review)

Random FEVER test claims through the real verifier and the grounded explainer. `gold` is the label FEVER assigns.

## Larry Wilmore is Catholic.
- verdict **not_enough_info** (87%) vs gold **not_enough_info** (correct)
- rationale: The claim is not verifiable from the retrieved evidence (87% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Larry Wilmore” [1]: “Elister L. " Larry " Wilmore (born October 30, 1961) is an American comedian, writer, producer, and actor.”
- summary: Larry Wilmore: Elister L. " Larry " Wilmore (born October 30, 1961) is an American comedian, writer, producer, and actor. Larry Wilmore: He serves as an executive producer for the ABC television series Black-ish.
- most important words: Catholic. (1.00), actor. (0.00), is (0.00)

## Danielle Cormack was born on December 26, 1970.
- verdict **supported** (77%) vs gold **supported** (correct)
- rationale: The claim is supported (77% confidence). The model reads “Danielle Cormack” [1] as supporting the claim: “Danielle Cormack (born 26 December 1970) is a stage and screen actress from New Zealand.”
- summary: Danielle Cormack: Danielle Cormack (born 26 December 1970) is a stage and screen actress from New Zealand. Danielle Cormack: Other works include the 2009 film, Separation City, and the Australian series Rake. Danielle Cormack: She also portrayed notorious Sydney underworld figure Kate Leigh in Underbelly: Razor.
- most important words: 1970) (1.00), 26 (0.98), December (0.60)

## Raees (film) features Nawazuddin Siddiqui as an extra.
- verdict **not_enough_info** (79%) vs gold **refuted** (WRONG)
- rationale: The claim is not verifiable from the retrieved evidence (79% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Raees (film)” [1]: “It stars Shah Rukh Khan, Mahira Khan and Nawazuddin Siddiqui.” Terms from the claim that none of the retrieved sentences mention: extra, features.
- summary: Raees (film): It stars Shah Rukh Khan, Mahira Khan and Nawazuddin Siddiqui. Raees (film): Raees (English: Wealthy) is a 2017 Indian action crime thriller film directed by Rahul Dholakia and produced by Gauri Khan, Ritesh Sidhwani and Farhan Akhtar under their banners Red Chillies Entertainment and Excel Entertainment.
- most important words: extra. (1.00), Nawazuddin (0.04), stars (0.04)

## Always premiered in August 1989.
- verdict **refuted** (52%) vs gold **not_enough_info** (WRONG)
- rationale: The claim is refuted (52% confidence). The model is uncertain, so treat this verdict with caution. The model reads “Always (1989 film)” [1] as conflicting with the claim: “Always is a 1989 American romantic comedy-drama film directed by Steven Spielberg and starring Richard Dreyfuss, Holly Hunter, John Goodman, introducing Brad Johnson, and featuring Audrey Hepburn's cameo in her final…” Difference in wording: the claim mentions premiered, August, which [1] does not; [1] mentions comedy-drama, 's, Dreyfuss, which the claim does not. Not found in any retrieved sentence: premiered, August.
- summary: Always (1989 film): Always is a 1989 American romantic comedy-drama film directed by Steven Spielberg and starring Richard Dreyfuss, Holly Hunter, John Goodman, introducing Brad Johnson, and featuring Audrey Hepburn's cameo in her final film appearance. Always (1989 film): The film, however, follows the same basic plot line: the spirit of a recently dead expert pilot mentors a newer pilot, while watching him fall in love with his surviving girlfriend. Always (1989 film): The names of the four principal characters of the earlier film are all the same, with the exception of the Ted Randall character, who is called Ted " Baker " in the remake and Pete's last name is " Sandich ", instead of " Sandidge ".
- most important words: August (1.00), premiered (0.87), Always (0.57)

## Tilda Swinton was born on November 5, 1960.
- verdict **supported** (71%) vs gold **supported** (correct)
- rationale: The claim is supported (71% confidence). The model reads “Tilda Swinton” [1] as supporting the claim: “Katherine Matilda " Tilda " Swinton (born 5 November 1960) is a British actress, performance artist, model, and fashion muse, known for her roles in independent and Hollywood films.” Not found in any retrieved sentence: born.
- summary: Tilda Swinton: Katherine Matilda " Tilda " Swinton (born 5 November 1960) is a British actress, performance artist, model, and fashion muse, known for her roles in independent and Hollywood films. Tilda Swinton: In 2005, Swinton was given the Richard Harris Award by the British Independent Film Awards in recognition of her contributions to the British film industry. Tilda Swinton: Swinton later starred in the dark romantic fantasy drama, Only Lovers Left Alive (2014).
- most important words: 5 (1.00), 1960) (0.99), November (0.97)

## Andrew Kevin Walker is Irish.
- verdict **not_enough_info** (67%) vs gold **refuted** (WRONG)
- rationale: The claim is not verifiable from the retrieved evidence (67% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Andrew Kevin Walker” [1]: “Andrew Kevin Walker (born August 14, 1964) is an American BAFTA-nominated screenwriter.”
- summary: Andrew Kevin Walker: Andrew Kevin Walker (born August 14, 1964) is an American BAFTA-nominated screenwriter. Andrew Kevin Walker: He is known for having written Seven (1995), for which he earned a nomination for the BAFTA Award for Best Original Screenplay, as well as several other films, including 8mm (1999), Sleepy Hollow (1999) and many uncredited script rewrites.
- most important words: Irish. (1.00), screenwriter. (0.18), BAFTA-nominated (0.09)

## Wish Upon is a supernatural horror thriller movie.
- verdict **supported** (86%) vs gold **supported** (correct)
- rationale: The claim is supported (86% confidence). The model reads “Wish Upon” [1] as supporting the claim: “Wish Upon is a 2017 supernatural horror thriller film directed by John R. Leonetti and starring Joey King, Ryan Phillipe, Ki Hong Lee, Shannon Purser, Sydney Park and Sherilyn Fenn.” Also “Horror film” [2]: “Horror may also overlap with the fantasy, supernatural fiction and thriller genres.” Not found in any retrieved sentence: movie.
- summary: Wish Upon: Wish Upon is a 2017 supernatural horror thriller film directed by John R. Leonetti and starring Joey King, Ryan Phillipe, Ki Hong Lee, Shannon Purser, Sydney Park and Sherilyn Fenn. Horror film: Horror may also overlap with the fantasy, supernatural fiction and thriller genres.
- most important words: supernatural (1.00), horror (0.30), thriller (0.28)

## TakePart is the digital division of Participant Media.
- verdict **supported** (89%) vs gold **supported** (correct)
- rationale: The claim is supported (89% confidence). The model reads “TakePart” [1] as supporting the claim: “TakePart is the digital division of Participant Media, a motion picture studio that focuses on issues of social justice.” Also “Participant Media” [2]: “The company finances and co-produces films, and its digital hub, TakePart serves millions of socially conscious consumers each month with daily articles, videos and opportunities to take action.”
- summary: TakePart: TakePart is the digital division of Participant Media, a motion picture studio that focuses on issues of social justice. Participant Media: The company finances and co-produces films, and its digital hub, TakePart serves millions of socially conscious consumers each month with daily articles, videos and opportunities to take action.
- most important words: Participant (1.00), digital (0.99), division (0.07)

## Bad Romance was successful.
- verdict **supported** (86%) vs gold **supported** (correct)
- rationale: The claim is supported (86% confidence). The model reads “Bad Romance” [1] as supporting the claim: “It achieved worldwide success by topping the charts in a variety of markets, ultimately selling 12 million copies worldwide, thus becoming one of the best-selling singles of all time.” Also “Bad Romance” [2]: “In the United States, " Bad Romance " peaked at number two on the Billboard Hot 100, and it has been certified eleven-times platinum by the Recording Industry Association of America (RIAA), having sold 5.6 million…” Also “Bad Romance” [3]: “It was nominated for numerous superlatives, including ten awards at the 2010 MTV Video Music Awards, where the singer won seven, including a recognition for Video of the Year.” Not found in any retrieved sentence: successful.
- summary: Bad Romance: It achieved worldwide success by topping the charts in a variety of markets, ultimately selling 12 million copies worldwide, thus becoming one of the best-selling singles of all time. Bad Romance: It was nominated for numerous superlatives, including ten awards at the 2010 MTV Video Music Awards, where the singer won seven, including a recognition for Video of the Year. Bad Romance: In the United States, " Bad Romance " peaked at number two on the Billboard Hot 100, and it has been certified eleven-times platinum by the Recording Industry Association of America (RIAA), having sold 5.6 million digital downloads as of April 2016.
- most important words: success (1.00), successful. (0.56), was (0.40)

## Robert Zemechkis has made movies across a wide variety of genres and is acclaimed.
- verdict **not_enough_info** (72%) vs gold **supported** (WRONG)
- rationale: The claim is not verifiable from the retrieved evidence (72% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Robert Zemeckis” [1]: “The movies he has directed have ranged across a wide variety of genres, for both adults and families.” Terms from the claim that none of the retrieved sentences mention: Zemechkis, acclaimed, made.
- summary: Robert Zemeckis: Credited as " one of the greatest visual storytellers in filmmaking ", he first came to public attention in the 1980s as the director of Romancing the Stone (1984) and the science-fiction comedy Back to the Future film trilogy, as well as the live-action/animated comedy Who Framed Roger Rabbit (1988). Robert Zemeckis: The movies he has directed have ranged across a wide variety of genres, for both adults and families.
- most important words: acclaimed. (1.00), genres (0.02), genres, (0.02)

## Taran Killam is a Buddhist.
- verdict **not_enough_info** (86%) vs gold **not_enough_info** (correct)
- rationale: The claim is not verifiable from the retrieved evidence (86% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Taran Killam” [1]: “Taran Hourie Killam (born April 1, 1982) is an American actor, comedian, and writer.”
- summary: Taran Killam: Taran Hourie Killam (born April 1, 1982) is an American actor, comedian, and writer. Taran Killam: He is best known for his television work on shows such as The Amanda Show, Wild 'n Out, Mad TV, and Saturday Night Live.
- most important words: Buddhist. (1.00), writer. (0.01), actor, (0.00)

## St. Anger is the eighth studio album by an American band.
- verdict **supported** (76%) vs gold **supported** (correct)
- rationale: The claim is supported (76% confidence). The model reads “St. Anger” [1] as supporting the claim: “St. Anger is the eighth studio album by American heavy metal band Metallica, released on June 5, 2003, by Elektra Records.” Also “St. Anger (song)” [2]: “It was released in June 2003 as the lead single from their eighth studio album of the same name.”
- summary: St. Anger: St. Anger is the eighth studio album by American heavy metal band Metallica, released on June 5, 2003, by Elektra Records. St. Anger (song): It was released in June 2003 as the lead single from their eighth studio album of the same name. St. Anger (song): " St. Anger " is a song by American heavy metal group Metallica.
- most important words: eighth (1.00), American (0.49), by (0.01)

## Christian Gottlob Neefe died in February 1798.
- verdict **supported** (72%) vs gold **refuted** (WRONG)
- rationale: The claim is supported (72% confidence). The model reads “Christian Gottlob Neefe” [1] as supporting the claim: “Christian Gottlob Neefe (5 February 1748 -- 28 January 1798) was a German opera composer and conductor.”
- summary: Christian Gottlob Neefe: Christian Gottlob Neefe (5 February 1748 -- 28 January 1798) was a German opera composer and conductor. Christian Gottlob Neefe: He died in Dessau. Christian Gottlob Neefe: Neefe was born in Chemnitz, Saxony.
- most important words: 1798) (1.00), February (0.50), -- (0.05)

## The ovary is an organ.
- verdict **supported** (91%) vs gold **supported** (correct)
- rationale: The claim is supported (91% confidence). The model reads “Ovary” [1] as supporting the claim: “The ovary (From ovarium, literally " egg " or " nut ") is an ovum-producing reproductive organ, found in pairs in the female as part of the vertebrate female reproductive system.” Also “Lymph node” [2]: “A lymph node or lymph gland, is an ovoid or kidney-shaped organ of the lymphatic system, and of the adaptive immune system, that is widely present throughout the body.” Also “Ovary” [3]: “Ovaries in females are analogous to testes in males, in that they are both gonads and endocrine glands.”
- summary: Ovary: The ovary (From ovarium, literally " egg " or " nut ") is an ovum-producing reproductive organ, found in pairs in the female as part of the vertebrate female reproductive system. Lymph node: A lymph node or lymph gland, is an ovoid or kidney-shaped organ of the lymphatic system, and of the adaptive immune system, that is widely present throughout the body. Frenulum: A frenulum (or frenum, plural: frenula or frena, from the Latin frēnulum, " little bridle ", the diminutive of frēnum) is a small fold of tissue that secures or restricts the motion of a mobile organ in the body.
- most important words: organ, (1.00), an (0.09), ovary (0.04)

## Starrcade was an annual professional wrestling event.
- verdict **supported** (88%) vs gold **supported** (correct)
- rationale: The claim is supported (88% confidence). The model reads “Starrcade” [1] as supporting the claim: “Starrcade was an annual professional wrestling event, originally broadcast via closed-circuit television and eventually broadcast via pay-per-view television, held from 1983 to 2000 by the National Wrestling Alliance…”
- summary: Starrcade: Starrcade was an annual professional wrestling event, originally broadcast via closed-circuit television and eventually broadcast via pay-per-view television, held from 1983 to 2000 by the National Wrestling Alliance (NWA) and later World Championship Wrestling (WCW). Starrcade: Starrcade was regarded by the NWA and WCW as their flagship event of the year, much in the same vein that its rival, the World Wrestling Entertainment, regards WrestleMania. Starrcade: In November 2008, WWE 24/7 Classics aired a special as a celebration of the 25th anniversary of the event called The Essential Starrcade.
- most important words: annual (1.00), professional (0.02), 2000 (0.00)

## Ingushetia was established in the U.S South Peninsula.
- verdict **refuted** (82%) vs gold **refuted** (correct)
- rationale: The claim is refuted (82% confidence). The model reads “Ingushetia” [1] as conflicting with the claim: “The Republic of Ingushetia ( Гӏалгӏай Мохк,), also referred to as simply Ingushetia, is a federal subject of Russia (a republic), located in the North Caucasus region.” Also “Ingushetia” [2]: “It was established on June 4, 1992 after the Chechen-Ingush Autonomous Soviet Socialist Republic was split in two.” Difference in wording: the claim mentions U.S, established, Peninsula, which [1] does not; [1] mentions located, Caucasus, subject, which the claim does not. Not found in any retrieved sentence: U.S, Peninsula, South.
- summary: Ingushetia: It was established on June 4, 1992 after the Chechen-Ingush Autonomous Soviet Socialist Republic was split in two. Ingushetia: The Republic of Ingushetia ( Гӏалгӏай Мохк,), also referred to as simply Ingushetia, is a federal subject of Russia (a republic), located in the North Caucasus region. Ingushetia: Ingushetia is one of Russia's poorest and most unstable regions.
- most important words: U.S (1.00), the (0.32), Ingushetia (0.30)

## Human trafficking leads to forced labor.
- verdict **supported** (87%) vs gold **not_enough_info** (WRONG)
- rationale: The claim is supported (87% confidence). The model reads “Human trafficking” [1] as supporting the claim: “Of these, 14.2 million (68%) were exploited for labor, 4.5 million (22%) were sexually exploited, and 2.2 million (10%) were exploited in state-imposed forced labor.” Also “Human trafficking” [2]: “Human trafficking is the trade of humans, most commonly for the purpose of forced labour, sexual slavery, or commercial sexual exploitation for the trafficker or others.” Also “Human trafficking” [3]: “According to the International Labour Organization (ILO), forced labor alone (one component of human trafficking) generates an estimated $ 150 billion in profits per annum as of 2014.” Not found in any retrieved sentence: leads.
- summary: Human trafficking: Human trafficking is the trade of humans, most commonly for the purpose of forced labour, sexual slavery, or commercial sexual exploitation for the trafficker or others. Human trafficking: According to the International Labour Organization (ILO), forced labor alone (one component of human trafficking) generates an estimated $ 150 billion in profits per annum as of 2014. Human trafficking: Of these, 14.2 million (68%) were exploited for labor, 4.5 million (22%) were sexually exploited, and 2.2 million (10%) were exploited in state-imposed forced labor.
- most important words: forced (1.00), to (0.36), trafficking (0.09)

## Bethany Hamilton was a victim of a shark attack.
- verdict **supported** (78%) vs gold **supported** (correct)
- rationale: The claim is supported (78% confidence). The model reads “Bethany Hamilton” [1] as supporting the claim: “Bethany Meilani Hamilton-Dirks (born February 8, 1990) is an American professional surfer who survived a 2003 shark attack in which her left arm was bitten off but who ultimately returned to -- and was victorious in --…” Not found in any retrieved sentence: victim.
- summary: Bethany Hamilton: Bethany Meilani Hamilton-Dirks (born February 8, 1990) is an American professional surfer who survived a 2003 shark attack in which her left arm was bitten off but who ultimately returned to -- and was victorious in -- professional surfing. Bethany Hamilton: She wrote about her experience in the 2004 autobiography Soul Surfer: A True Story of Faith, Family, and Fighting to Get Back on the Board.
- most important words: shark (1.00), victim (0.04), attack (0.01)

## Tylenol is a brand of cream.
- verdict **refuted** (77%) vs gold **refuted** (correct)
- rationale: The claim is refuted (77% confidence). The model reads “Tylenol (brand)” [1] as conflicting with the claim: “Tylenol is a brand of drugs advertised for reducing pain, reducing fever, and relieving the symptoms of allergies, cold, cough headache, and influenza.” Also “Tylenol (brand)” [2]: “The active ingredient of its original flagship product is paracetamol (known in the United States as acetaminophen), an analgesic and antipyretic.” Also “Tylenol (brand)” [3]: “Like the words acetaminophen and paracetamol, the brand name Tylenol is derived from the chemical name for the compound, N-aceTYL-para-aminophENOL (APAP).” Difference in wording: the claim mentions cream, which [1] does not; [1] mentions allergies, advertised, cough, which the claim does not. Not found in any retrieved sentence: cream.
- summary: Tylenol (brand): Tylenol is a brand of drugs advertised for reducing pain, reducing fever, and relieving the symptoms of allergies, cold, cough headache, and influenza. Tylenol (brand): Like the words acetaminophen and paracetamol, the brand name Tylenol is derived from the chemical name for the compound, N-aceTYL-para-aminophENOL (APAP). Tylenol (brand): As of 2017 the " Tylenol " brand was used in Brazil, Canada, China, Egypt, Lebanon, Myanmar, Oman, Philippines, Portugal, Spain, Switzerland, Thailand, United States, and Vietnam.
- most important words: cream. (1.00), drugs (0.52), of (0.38)

## Marvel vs. Capcom is part of a trilogy.
- verdict **not_enough_info** (70%) vs gold **refuted** (WRONG)
- rationale: The claim is not verifiable from the retrieved evidence (70% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Marvel vs. Capcom” [1]: “is a series of crossover fighting games developed and published by Capcom, featuring characters from their own video game franchises and comic book series published by Marvel Comics.” Terms from the claim that none of the retrieved sentences mention: part, trilogy.
- summary: Marvel vs. Capcom: Infinite: It is the sixth main entry in the Marvel vs. Capcom series of crossover games. Marvel vs. Capcom: Infinite: Infinite features two-on-two fights, as opposed to the three-on-three format used in its preceding titles.
- most important words: trilogy. (1.00), characters (0.06), Marvel (0.05)

## A near-Earth object is one whose orbit brings it into proximity with Earth and it is in the universe.
- verdict **supported** (70%) vs gold **supported** (correct)
- rationale: The claim is supported (70% confidence). The model reads “Near-Earth object” [1] as supporting the claim: “A near-Earth object (NEO) is any small Solar System body whose orbit brings it into proximity with Earth.” Not found in any retrieved sentence: universe.
- summary: Near-Earth object: A near-Earth object (NEO) is any small Solar System body whose orbit brings it into proximity with Earth. Near-Earth object: Some NEAs orbits intersect that of Earth's so they pose a collision danger.
- most important words: the (1.00), in (0.81), whose (0.14)

## Northwestern University is the only private university of the Midwest.
- verdict **supported** (41%) vs gold **not_enough_info** (WRONG)
- rationale: The claim is supported (41% confidence). The model is uncertain, so treat this verdict with caution. The model reads “Big Ten Conference” [1] as supporting the claim: “Northwestern University, one of just two full members with a total enrollment of fewer than 30,000 students (the other is the University of Nebraska -- Lincoln), is the lone private university among Big Ten membership…” Also “Northwestern University” [2]: “Northwestern is a founding member of the Big Ten Conference and remains the only private university in the conference.” Not found in any retrieved sentence: Midwest.
- summary: Northwestern University: Northwestern is a founding member of the Big Ten Conference and remains the only private university in the conference. Big Ten Conference: Northwestern University, one of just two full members with a total enrollment of fewer than 30,000 students (the other is the University of Nebraska -- Lincoln), is the lone private university among Big Ten membership (the University of Chicago, a private university, left the conference in 1946).
- most important words: lone (1.00), private (0.86), private (0.85)

## Scotty Moore was only German.
- verdict **refuted** (92%) vs gold **refuted** (correct)
- rationale: The claim is refuted (92% confidence). The model reads “Scotty Moore” [1] as conflicting with the claim: “Winfield Scott " Scotty " Moore III (December 27, 1931 -- June 28, 2016) was an American guitarist and recording engineer.” Also “Scotty Moore” [2]: “He is best known for his backing of Elvis Presley in the first part of his career, between 1954 and the beginning of Elvis's Hollywood years.” Also “Scotty Moore” [3]: “All I wanted to do in the world was to be able to play and sound like that.” Difference in wording: the claim mentions German, which [1] does not; [1] mentions Winfield, engineer, 1931, which the claim does not. Not found in any retrieved sentence: German.
- summary: Scotty Moore: Winfield Scott " Scotty " Moore III (December 27, 1931 -- June 28, 2016) was an American guitarist and recording engineer. Scotty Moore: It was as plain as day. Scotty Moore: Moore was ranked 29th in Rolling Stone magazine's list of 100 Greatest Guitarists of All Time in 2011.
- most important words: only (1.00), was (0.23), Scotty (0.08)

## Tijuana is on a landmass.
- verdict **supported** (84%) vs gold **supported** (correct)
- rationale: The claim is supported (84% confidence). The model reads “Tijuana” [1] as supporting the claim: “Tijuana is the largest city in Baja California and on the Baja California Peninsula and center of the Tijuana metropolitan area, part of the international San Diego -- Tijuana metropolitan area.” Also “Tijuana” [2]: “Tijuana is located on the Gold Coast of Baja California, and is the municipal seat and cultural and commercial center of Tijuana Municipality.” Also “Tijuana” [3]: “Tijuana is the 45th largest city in the Americas and is the westernmost city in Mexico.” Not found in any retrieved sentence: landmass.
- summary: Tijuana: Tijuana is located on the Gold Coast of Baja California, and is the municipal seat and cultural and commercial center of Tijuana Municipality. Tijuana: Tijuana is the 45th largest city in the Americas and is the westernmost city in Mexico. Tijuana: Tijuana traces its modern history to the arrival of Spanish explorers in the 16th century who were mapping the coast of the Californias.
- most important words: a (1.00), ([tiːˈwɑːnə]; (0.86), [tiˈxwana]) (0.69)

## Military deception overlaps with psychological warfare.
- verdict **supported** (89%) vs gold **supported** (correct)
- rationale: The claim is supported (89% confidence). The model reads “Military deception” [1] as supporting the claim: “As a form of strategic use of information (disinformation), it overlaps with psychological warfare.” Also “Military deception” [2]: “This is usually achieved by creating or amplifying an artificial fog of war via psychological operations, information warfare, visual deception and other methods.”
- summary: Military deception: As a form of strategic use of information (disinformation), it overlaps with psychological warfare. Military deception: This is usually achieved by creating or amplifying an artificial fog of war via psychological operations, information warfare, visual deception and other methods.
- most important words: psychological (1.00), warfare. (0.12), overlaps (0.04)

## Saturn Corporation is a registered voter.
- verdict **not_enough_info** (80%) vs gold **refuted** (WRONG)
- rationale: The claim is not verifiable from the retrieved evidence (80% confidence). No retrieved sentence clearly confirms or contradicts it. The closest evidence is “Saturn Corporation” [1]: “The Saturn Corporation, also known as Saturn LLC, is a registered trademark established on January 7, 1985, as a subsidiary of General Motors.” Terms from the claim that none of the retrieved sentences mention: voter.
- summary: Saturn Corporation: The Saturn Corporation, also known as Saturn LLC, is a registered trademark established on January 7, 1985, as a subsidiary of General Motors. Saturn Corporation: The company marketed itself as a " different kind of car company " and operated somewhat independently from its parent company for a time with its own assembly plant in Spring Hill, Tennessee; unique models; and a separate retailer network, and was GM's attempt to compete with Japanese automakers.
- most important words: voter. (1.00), is (0.04), registered (0.04)

## The Ellen Show broadcast on ABC.
- verdict **supported** (71%) vs gold **refuted** (WRONG)
- rationale: The claim is supported (71% confidence). The model reads “Ellen (TV series)” [1] as supporting the claim: “Ellen is an American television sitcom that aired on the ABC network from March 29, 1994, to July 22, 1998, consisting of 109 episodes.”
- summary: Ellen (TV series): Ellen is an American television sitcom that aired on the ABC network from March 29, 1994, to July 22, 1998, consisting of 109 episodes. The Ellen Show: The Ellen Show is a television sitcom created by and starring Ellen DeGeneres that was broadcast during the 2001 -- 02 season on CBS. The Ellen DeGeneres Show: The Ellen DeGeneres Show (often shortened to Ellen) is an American television comedy talk show hosted by comedienne/actress Ellen DeGeneres.
- most important words: ABC (1.00), on (0.00), aired (0.00)

## Chris Mullin played with a professional basketball team.
- verdict **supported** (92%) vs gold **supported** (correct)
- rationale: The claim is supported (92% confidence). The model reads “Chris Mullin (basketball)” [1] as supporting the claim: “Christopher Paul Mullin (born July 30, 1963) is an American retired professional basketball player and current head coach of the St. John's Red Storm.” Also “Chris Mullin (basketball)” [2]: “He retired after the 2000 -- 01 season, playing for his original team, the Warriors.” Also “Chris Mullin (basketball)” [3]: “Mullin played shooting guard and small forward in the NBA from 1985 to 2001.”
- summary: Chris Mullin (basketball): He returned to the Olympics in 1992 as a member of the " Dream Team ", which was the first American Olympic basketball team to include professional players. Chris Mullin (basketball): Mullin played shooting guard and small forward in the NBA from 1985 to 2001. Chris Mullin (basketball): Christopher Paul Mullin (born July 30, 1963) is an American retired professional basketball player and current head coach of the St. John's Red Storm.
- most important words: a (1.00), professional (0.93), basketball (0.29)

## See You on the Other Side is a boat.
- verdict **refuted** (81%) vs gold **refuted** (correct)
- rationale: The claim is refuted (81% confidence). The model reads “See You on the Other Side (Korn album)” [1] as conflicting with the claim: “See You on the Other Side is the seventh studio album by Korn.” Difference in wording: the claim mentions boat, which [1] does not; [1] mentions Korn, seventh, studio, which the claim does not.
- summary: See You on the Other Side (Korn album): See You on the Other Side is the seventh studio album by Korn. Have You Seen the Other Side of the Sky?: Have You Seen the Other Side of the Sky?
- most important words: boat. (1.00), is (0.92), a (0.28)

## The Siege of Fort Stanwix began on August 2, 1777.
- verdict **supported** (79%) vs gold **supported** (correct)
- rationale: The claim is supported (79% confidence). The model reads “Siege of Fort Stanwix” [1] as supporting the claim: “The Siege of Fort Stanwix (also known at the time as Fort Schuyler) began on August 2, 1777, and ended August 22.”
- summary: Siege of Fort Stanwix: The Siege of Fort Stanwix (also known at the time as Fort Schuyler) began on August 2, 1777, and ended August 22. Fort Stanwix: Fort Stanwix was a colonial fort whose construction commenced on August 26, 1758, under the direction of British General John Stanwix, at the location of present-day Rome, New York, but was not completed until about 1762. Siege of Fort Stanwix: Fort Stanwix, in the western part of the Mohawk River Valley, was then the primary defense point for the Continental Army against British and Indian forces aligned against them in the American Revolutionary War.
- most important words: 1777, (1.00), 2, (0.87), The (0.00)
