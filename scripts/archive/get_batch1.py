import csv

schools = []
with open("verified_dataset.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("confidence") != "verified":
            try:
                enroll = int(float(row.get("enrollment") or 0))
            except:
                enroll = 0
            schools.append((enroll, row["school_name"], row["state"]))

schools.sort(reverse=True)
print("Top 10 unverified schools by enrollment:")
for idx, (enroll, name, state) in enumerate(schools[:10]):
    print(f"{idx+1}. {name} ({state}) - {enroll:,} students")
