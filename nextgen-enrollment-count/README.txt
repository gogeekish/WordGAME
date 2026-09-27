NEXTGEN ENROLLMENT COUNT — OFFLINE DESKTOP TOOL

WHAT IT DOES
1. Paste your document (any size) into the "Paste Your Document" box.
2. Paste the words/IDs you want to search for into the second box — one per
   line. There is no limit; you can paste 200 or more at once.
3. Click "Count Results".
4. The app finds every line that has a date like "03-Aug-2026" in it, works
   out its Month + Year (for example "Aug 2026"), and counts how many times
   each of your search words appears in that Month + Year.
5. A table appears on screen (one row per Month+Year that actually shows up
   in your data — for example "Jan 2026" and "Jan 2025" are always counted
   separately, never mixed together).
6. Click "Download Excel (.xlsx)" to save the full table as a real Excel
   file. The file is named "NextGen-Enrollment-Count-<date>.xlsx" and is
   saved to your Downloads folder.

HOW TO RUN IT
1. Copy "NextGen Enrollment Count 1.0.0.exe" onto your Windows computer.
2. Double-click it. No installer, no internet connection needed — everything
   runs entirely on your own computer.
3. Windows may show a "protected your PC" warning because the app isn't
   signed by a paid certificate — click "More info" then "Run anyway".

NOTES
- This is a completely separate app from Word Arena TV — it does not touch
  or affect that program in any way, and does not need to be installed in
  the same folder.
- Matching is not case-sensitive, so "HENA-123" and "hena-123" are treated
  as the same search word.
- If you paste the same search word twice (even with different capital
  letters), it only counts once.

BUILDING YOUR OWN .EXE (only needed if you change the code)
1. npm install
2. npm run dist
3. The finished file appears in the "dist" folder.
