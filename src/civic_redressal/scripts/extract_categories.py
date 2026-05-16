import csv

categories = set()
with open('data/train.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        categories.add(row['category_title'])

print('Unique category_title values:')
for cat in sorted(categories):
    print(f'  "{cat}"')