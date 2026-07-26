from app import app, db, Product

with app.app_context():

    product = Product(
        name="Fox Premium Image",
        description="A special artwork",
        price=5.00,
        image="locked.png"
    )

    db.session.add(product)
    db.session.commit()

    print("Product added!")