from app import app, db
from models import Customer

with app.app_context():
    customers = Customer.query.all()
    print(f'Total customers: {len(customers)}')

    # Analyse de la diversité des genres
    diversity = {}
    for c in customers:
        g = c.gender
        if g in diversity:
            diversity[g] += 1
        else:
            diversity[g] = 1
    print(f'Gender distribution: {diversity}')

    # Analyse de la distribution des âges
    ages = {}
    for c in customers:
        if c.age:
            a = (c.age // 10) * 10
            key = f'{a}-{a+9}'
            if key in ages:
                ages[key] += 1
            else:
                ages[key] = 1
    print(f'Age distribution: {ages}')

    # Analyse des pays
    countries = {}
    for c in customers:
        country = c.country_code
        if country in countries:
            countries[country] += 1
        else:
            countries[country] = 1
    print(f'Country distribution: {countries}')

    # Analyse des intérêts
    interest_counts = {}
    for c in customers:
        if c.interests:
            for interest in c.get_interests_list():
                if interest in interest_counts:
                    interest_counts[interest] += 1
                else:
                    interest_counts[interest] = 1
    
    top_interests = sorted(interest_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f'Top interests: {top_interests}')
