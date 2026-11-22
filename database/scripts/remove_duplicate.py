with open("services/api/app/staff/router.py", "r", encoding="utf-8") as f:
    text = f.read()

dup_marker = "class StaffComplaintItem(BaseModel):"
first_idx = text.find(dup_marker)
second_idx = text.find(dup_marker, first_idx + len(dup_marker))
res_marker = '@router.post("/issues/{issue_id}/resolution")'
end_dup = text.find(res_marker, second_idx)

assert second_idx != -1 and end_dup != -1, "Duplicate markers not found!"

new_text = text[:second_idx] + text[end_dup:]
with open("services/api/app/staff/router.py", "w", encoding="utf-8") as f:
    f.write(new_text)

print(f"Successfully removed duplicate block from staff/router.py. Old len: {len(text)}, New len: {len(new_text)}")
