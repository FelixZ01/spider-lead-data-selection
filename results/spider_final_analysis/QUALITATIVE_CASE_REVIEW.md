# Qualitative Case Review

## Evidence boundary

The cases below were manually checked from the saved predictions of all five seeds. They are used to explain model behaviour, not to replace official Spider exact match. Normalized string exact match is especially sensitive to formatting and quotation differences, so cases with only cosmetic differences are excluded from the substantive conclusions.

## Case A: grouping and HAVING - IDU-only advantage

- Example: `spider_000371_cre_Doc_Template_Mgt`
- Question: List all document ids with at least two paragraphs.
- Gold: `SELECT document_id FROM Paragraphs GROUP BY document_id HAVING count(*) >= 2`
- IDU-only: generated the correct `Paragraphs + GROUP BY + HAVING` structure in four of five seeds.
- Random: failed in all five seeds, commonly selecting the `Documents` table or replacing `HAVING count(*) >= 2` with `ORDER BY ... LIMIT 2`.

Interpretation: the IDU-only method appears to have improved a compositional pattern requiring the correct table, aggregation, grouping, and post-aggregation filtering. This is consistent with its positive official F1 differences for SELECT, SELECT without aggregation, WHERE without operator, and GROUP without HAVING, although it is only one example.

## Case B: schema linking and comparison operator - IDU-only advantage

- Example: `spider_000702_world_1`
- Question: What are the names of all the countries that became independent after 1950?
- Gold: `SELECT Name FROM country WHERE IndepYear > 1950`
- IDU-only: produced the direct correct query in four of five seeds.
- Random: often selected the `city` table, used equality instead of `>`, or linked 1950 to the wrong column.

Interpretation: the difference is mainly schema linking plus operator choice. It supports the view that iterative loss-change selection can emphasise examples that correct specific remaining weaknesses, but it does not show that all schema-linking errors are reduced.

## Case C: negation - Random advantage

- Example: `spider_000681_poker_player`
- Question: Show names of people whose nationality is not "Russia".
- Gold: `SELECT Name FROM people WHERE Nationality != "Russia"`
- Random: produced the intended inequality in four of five seeds.
- IDU-only: failed in all five seeds, usually reversing the condition to equality or generating an unnecessary nested `NOT IN` structure.

Interpretation: IDU-only can over-specialise toward selected high-utility patterns while missing simple but important logical operators. The method therefore improves the average result without uniformly improving every SQL skill.

## Case D: literal preservation - Random advantage

- Example: `spider_000619_tvshow`
- Question: What is the air date of TV series with Episode "A Love of a Lifetime"?
- Gold: `SELECT Air_Date FROM TV_series WHERE Episode = "A Love of a Lifetime"`
- Random: preserved the complete literal in four of five seeds.
- IDU-only: failed in all five seeds by shortening the literal or choosing a nonexistent output column.

Interpretation: iterative selection did not improve exact literal copying in this case. This is a useful counterexample to any claim that higher average exact match implies a general improvement across all error types.

## Excluded formatting-only cases

Some automatically detected disagreements differed only in quotation style or identifier capitalisation. These can be counted differently by normalized string matching even when the SQL meaning is unchanged. They are not used as evidence for a substantive method advantage.

## Consolidated conclusion

The manually checked cases support a cautious interpretation: IDU-only sometimes improves multi-part structural and schema-linking decisions, but it can lose simple negation and literal-preservation behaviours that Random retains. This mixed behaviour explains why IDU-only has the highest selected-data mean yet wins only three of five seeds and does not establish statistically conclusive superiority.
