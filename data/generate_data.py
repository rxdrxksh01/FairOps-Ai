import pandas as pd
import numpy as np

np.random.seed(42)
n = 1000

data = pd.DataFrame({
    'applicant_id': range(1, n+1),
    'age': np.random.randint(22, 65, n),
    'gender': np.random.choice(['Male', 'Female'], n, p=[0.6, 0.4]),
    'region': np.random.choice(['Urban', 'Semi-Urban', 'Rural'], n, p=[0.5, 0.3, 0.2]),
    'income_monthly': np.random.randint(8000, 120000, n),
    'existing_loans': np.random.randint(0, 4, n),
    'credit_score': np.random.randint(300, 850, n),
    'loan_amount_requested': np.random.randint(50000, 500000, n),
    'medical_condition': np.random.choice(['Cardiac', 'Orthopedic', 'Cancer', 'Neurological', 'General'], n),
    'employment_type': np.random.choice(['Salaried', 'Self-Employed', 'Daily Wage', 'Unemployed'], n, p=[0.45, 0.25, 0.2, 0.1]),
})

def assign_approval(row):
    score = 0
    if row['credit_score'] > 650: score += 3
    if row['income_monthly'] > 30000: score += 2
    if row['existing_loans'] < 2: score += 1
    if row['region'] == 'Urban': score += 2
    if row['employment_type'] == 'Salaried': score += 2
    if row['region'] == 'Rural': score -= 2
    if row['employment_type'] == 'Daily Wage': score -= 2
    return 1 if score >= 4 else 0

data['approved'] = data.apply(assign_approval, axis=1)
data.to_csv('sample_medical_loans.csv', index=False)

print(f"✅ Dataset generated: {len(data)} records")
print(f"📊 Overall approval rate: {data['approved'].mean():.1%}")
print(f"\n🔍 Approval by region:")
print(data.groupby('region')['approved'].mean().round(3))
print(f"\n🔍 Approval by employment:")
print(data.groupby('employment_type')['approved'].mean().round(3))