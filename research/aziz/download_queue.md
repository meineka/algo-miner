# Aziz Download Queue (run outside sandbox)

The Claude Code sandbox blocks direct egress to YouTube, SSRN,
bearbulltraders.com, alphatrends.net and several others
(`HTTP 403 host_not_allowed`). The list below is what to grab when
running outside the sandbox so the knowledge base can be fed with
primary-source text.

## YouTube (auto-captions via `yt-dlp`)

```bash
mkdir -p research/aziz/youtube
cd research/aziz/youtube

for vid in PFnvcZ_ni3I 7gLocbf6Lto 6-eEj8g6xdI MmQdPu7JYHk \
           4T8vxEWgTLs fbeUeCtpFOg S1i8wlQVNYY ADFMxPaqhQo \
           cimqvvFtJbY ePe7VbQumOg YGbt_3vnnhk c_fX5srrMqo \
           yBRLLj_WthY; do
  yt-dlp --write-auto-subs --skip-download --sub-format vtt \
         --sub-langs en --output "%(id)s.%(ext)s" \
         "https://www.youtube.com/watch?v=$vid"
done
```

## Bear Bull Traders PDFs

```
https://bearbulltraders.com/wp-content/uploads/2018/01/Session-4.pdf
https://bearbulltraders.com/wp-content/uploads/2023/03/Strategy-1-Three-Powerful-Day-Trading-TradeBooks-Andrew.pdf
https://bearbulltraders.com/docs/AndrewAziz-How_to_Day_Trade_for_a_Living_AUDIOBOOK-FIGS.pdf
```

## SSRN papers (PDF behind login but abstract pages are free)

```
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622   # Can Day Trading Really Be Profitable? (2023)
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4631351   # VWAP — The Holy Grail (2023)
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284   # Profitable Day Trading Strategy (2024)
```

## Podcasts / interviews

```
https://www.theinvestorspodcast.com/millennial-investing/mi009-day-trading-for-a-living-with-andrew-aziz/
https://alphatrends.net/archives/podcast/trading-vwap-discussion-with-andrew-aziz/
```

## Books (legal copies via Amazon)

- *How to Day Trade for a Living* — Andrew Aziz, ISBN 978-1535585958
- *Advanced Techniques in Day Trading* — Andrew Aziz, ISBN 978-1721151264
