import json
import csv
from flask import Flask, Response, stream_with_context, render_template, request, redirect, url_for, session, flash
from passlib.hash import pbkdf2_sha256

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Secret key for session management

# Paths to JSON files
PRODUCTS_FILE = "data/products.json"
NOTES_FILE = "data/notes.json"
USERS_FILE = "data/users.json"
COMPOSITIONS_FILE = "data/compositions.json"
PRODUCT_NOTES_FILE = "data/product_notes.json"
PRODUCT_COMPOSITIONS_FILE = "data/product_compositions.json"
RANGES_FILE = "data/ranges.json"

# In-memory data storage
products = []
notes = []
compositions = []
product_notes = []
product_compositions = []
ranges = []
users = []

def save_users():
    """Save users to JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_users():
    """Load users from JSON file."""
    global users
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []

# Load user data at startup
load_users()

def save_data():
    """Save data to JSON files."""
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(products, f, indent=4)
    with open(NOTES_FILE, 'w') as f:
        json.dump(notes, f, indent=4)
    with open(COMPOSITIONS_FILE, 'w') as f:
        json.dump(compositions, f, indent=4)
    with open(PRODUCT_NOTES_FILE, 'w') as f:
        json.dump(product_notes, f, indent=4)
    with open(PRODUCT_COMPOSITIONS_FILE, 'w') as f:
        json.dump(product_compositions, f, indent=4)
    with open(RANGES_FILE, 'w') as f:
        json.dump(ranges, f, indent=4)

def load_data():
    """Load data from JSON files."""
    global products, notes, compositions, product_notes, product_compositions, ranges
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            products = json.load(f)
    except FileNotFoundError:
        products = []

    try:
        with open(NOTES_FILE, 'r') as f:
            notes = json.load(f)
    except FileNotFoundError:
        notes = []

    try:
        with open(COMPOSITIONS_FILE, 'r') as f:
            compositions = json.load(f)
    except FileNotFoundError:
        compositions = []

    try:
        with open(PRODUCT_NOTES_FILE, 'r') as f:
            product_notes = json.load(f)
    except FileNotFoundError:
        product_notes = []

    try:
        with open(PRODUCT_COMPOSITIONS_FILE, 'r') as f:
            product_compositions = json.load(f)
    except FileNotFoundError:
        product_compositions = []

    try:
        with open(RANGES_FILE, 'r') as f:
            ranges = json.load(f)
    except FileNotFoundError:
        ranges = []

# Load data when the app starts
load_data()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        # If user is already logged in, redirect to /ItemTable
        return redirect(url_for('item_table'))
    
    """Login and Registration page."""
    if request.method == 'POST':
        if 'login' in request.form:
            # Handle login
            username = request.form['username']
            password = request.form['password']
            user = next((u for u in users if u['username'] == username), None)
            if user and pbkdf2_sha256.verify(password, user['password']):  # Verify the hashed password
                session['username'] = user['username']
                session['type'] = user['type']
                return redirect(url_for('index'))
            else:
                flash("Invalid credentials. Please try again.")
        elif 'register' in request.form:
            # Handle registration
            username = request.form['username']
            password = request.form['password']
            if any(u['username'] == username for u in users):
                flash("Username already exists. Please choose a different one.")
            else:
                hashed_password = pbkdf2_sha256.hash(password)  # Hash the password
                users.append({'username': username, 'password': hashed_password, 'type': 'user'})
                save_users()
                flash("Registration successful! You can now log in.")
                return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the user."""
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

def checkAuth():
    """Check if the user is authenticated or redirect to login."""
    if not users:
        # Redirect to login/register if no users are registered
        flash("No users registered. Please create an account first.")
        return redirect(url_for('login'))
    
    if 'username' not in session:
        # Redirect to login/register if the user is not logged in
        flash("Please log in to access this page.")
        return redirect(url_for('login'))
    
    # Return None if authentication is valid
    return None
    
@app.route('/')
def index():
    auth_redirect = checkAuth()
    if auth_redirect :
        return auth_redirect
    
    """Display all products in a table with sorting and filtering."""
    # Get sorting parameters from query string
    sort_column = request.args.get('sort', 'name')  # Default to sorting by Product Name
    sort_order = request.args.get('order', 'asc')  # Default to ascending order

    # Get filter parameters from query string
    selected_ranges = request.args.getlist('ranges')
    selected_ranges = [int(r) for r in selected_ranges if r.isdigit()]  # Convert to integers

    selected_names = request.args.getlist('name')  # Get a list of selected product names
    selected_names = [name.strip().lower() for name in selected_names]  # Clean and normalize names

    selected_notes = request.args.getlist('notes')
    selected_compositions = request.args.getlist('compositions')
    selected_format = request.args.get('format', None)
    min_price = request.args.get('min_price', None, type=float)
    max_price = request.args.get('max_price', None, type=float)

    # Attach range names to products and fetch related notes/compositions
    filtered_products = []
    for product in products:
        # Get range name
        range_name = next((r['name'] for r in ranges if r['id'] == product['id_range']), "Unknown")
        
        # Get notes for the product
        related_notes = [n['name'] for n in notes if any(pn['id_note'] == n['id'] and pn['id_product'] == product['id'] for pn in product_notes)]
        
        # Get compositions for the product
        related_compositions = [c['name'] for c in compositions if any(pc['id_composition'] == c['id'] and pc['id_product'] == product['id'] for pc in product_compositions)]
        
        # Add processed data to the product
        processed_product = {
            **product,
            'range_name': range_name,
            'notes': related_notes,
            'compositions': related_compositions,
        }

        # Apply filters
        if selected_ranges and product['id_range'] not in selected_ranges:
            continue
        if selected_names and not any(product['name'].lower() == name for name in selected_names):
            continue
        if selected_notes and not any(note in related_notes for note in selected_notes):
            continue
        if selected_compositions and not any(composition in related_compositions for composition in selected_compositions):
            continue
        if selected_format and selected_format != product['format']:
            continue

        # Add filtered product to the list
        filtered_products.append(processed_product)

    # Sort the products
    reverse = (sort_order == 'desc')
    filtered_products.sort(key=lambda x: x.get(sort_column, '').lower() if isinstance(x.get(sort_column), str) else x.get(sort_column), reverse=reverse)

    return render_template(
        'index.html',
        products=filtered_products,
        ranges=ranges,
        notes=notes,
        compositions=compositions,
        formats=set(p['format'] for p in products),
        sort_column=sort_column,
        sort_order=sort_order,
        selected_ranges=selected_ranges,
        selected_names=selected_names,
    )

@app.route('/export_csv')
def export_csv():    
    """Export selected product details as a CSV with multi-relational Notes and Composition."""
    auth_redirect = checkAuth()
    if auth_redirect :
        return auth_redirects

    # Get filter parameters
    min_price = request.args.get('min_price', None, type=float)
    max_price = request.args.get('max_price', None, type=float)
    selected_ranges = request.args.getlist('ranges', type=int)
    selected_names = request.args.getlist('name')
    selected_notes = request.args.getlist('notes')
    selected_compositions = request.args.getlist('compositions')
    sort_column = request.args.get('sort', 'name')
    sort_order = request.args.get('order', 'asc')

    # Log received filters
    print(f"Min Price: {min_price}, Max Price: {max_price}")
    print(f"Selected Ranges: {selected_ranges}")
    print(f"Selected Names: {selected_names}")
    print(f"Selected Notes: {selected_notes}")
    print(f"Selected Compositions: {selected_compositions}")
    print(f"Sort Column: {sort_column}, Sort Order: {sort_order}")

    # Build relational mappings for Notes and Compositions
    product_notes_mapping = {}
    for pn in product_notes:
        if pn['id_product'] not in product_notes_mapping:
            product_notes_mapping[pn['id_product']] = []
        note = next((n['name'] for n in notes if n['id'] == pn['id_note']), None)
        if note:
            product_notes_mapping[pn['id_product']].append(note)

    product_compositions_mapping = {}
    for pc in product_compositions:
        if pc['id_product'] not in product_compositions_mapping:
            product_compositions_mapping[pc['id_product']] = []
        composition = next((c['name'] for c in compositions if c['id'] == pc['id_composition']), None)
        if composition:
            product_compositions_mapping[pc['id_product']].append(composition)

    # Filter products
    filtered_products = []
    for product in products:
        # Apply filters
        if selected_ranges and product['id_range'] not in selected_ranges:
            continue
        if selected_names and product['name'] not in selected_names:
            continue
        if selected_notes and not any(note in product_notes_mapping.get(product['id'], []) for note in selected_notes):
            continue
        if selected_compositions and not any(comp in product_compositions_mapping.get(product['id'], []) for comp in selected_compositions):
            continue
        if min_price is not None and product[price_type] < min_price:
            continue
        if max_price is not None and product[price_type] > max_price:
            continue

        filtered_products.append(product)

    # Debug filtered products
    print(f"Filtered Products: {[p['name'] for p in filtered_products]}")

    # Sort products
    reverse = sort_order == 'desc'
    filtered_products.sort(key=lambda x: x.get(sort_column, '').lower() if isinstance(x.get(sort_column), str) else x.get(sort_column), reverse=reverse)

    # Debug sorted products
    print(f"Sorted Products: {[p['name'] for p in filtered_products]}")

    # Create CSV response
    def generate_csv():
        # Headers
        yield 'Range;Product Name;Format;Retail Price;Cost;Description;Notes;Composition\n'
    
        # Write filtered product details
        for product in filtered_products:
            notes = ', '.join(product_notes_mapping.get(product['id'], []))  # Internal separator: ","
            compositions = ', '.join(product_compositions_mapping.get(product['id'], []))  # Internal separator: ","
            row = [
                product.get('range_name', ''),
                product.get('name', ''),
                product.get('format', ''),
                str(product.get('cost', '')),
                product.get('description', '').replace('\n', ' '),  # Avoid newlines in description
                notes,
                compositions
            ]
            yield ';'.join(row) + '\n'  # Column separator: ";"

    return Response(
        stream_with_context(generate_csv()),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=product_details.csv"}
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Display details of a product with its notes and compositions."""
    auth_redirect = checkAuth()
    if auth_redirect :
        return auth_redirect
    
    # Find the product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404

    # Retrieve related notes
    related_notes = [n['name'] for n in notes if any(pn['id_note'] == n['id'] and pn['id_product'] == product_id for pn in product_notes)]

    # Retrieve related compositions
    related_compositions = [c['name'] for c in compositions if any(pc['id_composition'] == c['id'] and pc['id_product'] == product_id for pc in product_compositions)]

    return render_template('product_detail.html', product=product, notes=related_notes, compositions=related_compositions)

@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    """Add a new product with notes, compositions, and range."""
    auth_redirect = checkAuth()
    if auth_redirect:
        return auth_redirect

    if request.method == 'POST':
        # Collect product data
        product_id = len(products) + 1
        name = request.form['name']
        description = request.form['description']
        format_ = request.form['format']
        range_id = int(request.form['range'])
        
        # Handle notes
        selected_notes = request.form.getlist('notes')
        new_notes = request.form.getlist('new_notes')
        for note_name in new_notes:
            if note_name.strip():
                new_note_id = len(notes) + 1
                notes.append({'id': new_note_id, 'name': note_name})
                product_notes.append({'id': len(product_notes) + 1, 'id_product': product_id, 'id_note': new_note_id})
        for note in selected_notes:
            product_notes.append({'id': len(product_notes) + 1, 'id_product': product_id, 'id_note': int(note)})

        # Handle compositions
        selected_compositions = request.form.getlist('compositions')
        new_compositions = request.form.getlist('new_compositions')
        product_compositions_list = []
        for composition_name in new_compositions:
            if composition_name.strip():
                new_composition_id = len(compositions) + 1
                compositions.append({'id': new_composition_id, 'name': composition_name, 'price': 0.0})  # Default price
                product_compositions.append({'id': len(product_compositions) + 1, 'id_product': product_id, 'id_composition': new_composition_id})
        for composition in selected_compositions:
            product_compositions.append({'id': len(product_compositions) + 1, 'id_product': product_id, 'id_composition': int(composition)})
            product_compositions_list.append(int(composition))

        # Calculate cost based on selected compositions
        cost = sum(comp['price'] for comp in compositions if comp['id'] in product_compositions_list)

        # Add product to the database
        products.append({
            'id': product_id,
            'name': name,
            'description': description,
            'format': format_,
            'cost': cost,
            'id_range': range_id
        })

        save_data()  # Save the updated data
        flash(f"Product {name} added successfully!")
        return redirect(url_for('index'))

    return render_template('add_product.html', notes=notes, compositions=compositions, ranges=ranges)

@app.route('/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Delete a product and its related entries in product_notes and product_compositions."""
    auth_redirect = checkAuth()
    if auth_redirect :
        return auth_redirect
    
    global products, product_notes, product_compositions

    # Remove the product from products
    products = [p for p in products if p['id'] != product_id]

    # Remove related entries in product_notes and product_compositions
    product_notes = [pn for pn in product_notes if pn['id_product'] != product_id]
    product_compositions = [pc for pc in product_compositions if pc['id_product'] != product_id]

    # Save updated data back to JSON files
    save_data()

    return redirect(url_for('index'))

def recalculate_product_cost(product_id):
    """Recalculate the cost of a product based on its components."""
    product_comps = [pc for pc in product_compositions if pc['id_product'] == product_id]
    component_ids = [pc['id_composition'] for pc in product_comps]
    cost = sum(comp['price'] for comp in compositions if comp['id'] in component_ids)
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        product['cost'] = cost
        save_data()

@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    """Admin-only page to manage users."""
    auth_redirect = checkAuth()
    if auth_redirect:
        return auth_redirect

    # Ensure only admin can access this page
    if session.get('type') != 'admin':
        flash("You do not have permission to access this page.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Add new user
        username = request.form['username']
        password = request.form['password']
        if any(u['username'] == username for u in users):
            flash("Username already exists. Please choose a different one.")
        else:
            hashed_password = pbkdf2_sha256.hash(password)  # Hash the password
            users.append({'username': username, 'password': hashed_password, 'type': 'user'})
            save_users()
            flash(f"User {username} added successfully.")

    # Pass users to the template
    return render_template('manage_users.html', users=users)
    
@app.route('/update_user_role/<username>', methods=['POST'])
def update_user_role(username):
    """Update the role of a user."""
    auth_redirect = checkAuth()
    if auth_redirect:
        return auth_redirect

    # Ensure only admin can perform this action
    if session.get('type') != 'admin':
        flash("You do not have permission to update user roles.")
        return redirect(url_for('manage_users'))

    # Find the user
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash("User not found.")
        return redirect(url_for('manage_users'))

    # Update the user's role
    new_role = request.form.get('role')
    if new_role in ['user', 'manager', 'admin']:
        user['type'] = new_role
        save_users()  # Save updated users to the JSON file
        flash(f"Role for {username} updated to {new_role}.")
    else:
        flash("Invalid role selected.")

    return redirect(url_for('manage_users'))

@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    """Delete a user."""
    auth_redirect = checkAuth()
    if auth_redirect:
        return auth_redirect

    # Ensure only admin can perform this action
    if session.get('type') != 'admin':
        flash("You do not have permission to delete users.")
        return redirect(url_for('manage_users'))

    # Ensure the admin cannot delete themselves
    if username == session.get('username'):
        flash("You cannot delete yourself.")
        return redirect(url_for('manage_users'))

    # Remove the user from the list
    global users
    users = [u for u in users if u['username'] != username]
    save_users()  # Save updated users to the JSON file
    flash(f"User {username} deleted successfully.")

    return redirect(url_for('manage_users'))


if __name__ == '__main__':
    app.run(debug=True)