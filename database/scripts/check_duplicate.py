with open("services/api/app/staff/router.py", "r", encoding="utf-8") as f:
    text = f.read()

first_idx = 5006
end_first = text.find('@router.post("/triage/{issue_id}")', first_idx)
print("First all-complaints block length:", end_first - first_idx)
print("First 500 chars:\n", text[first_idx:first_idx+500])
