import json
import csv
from flask import Flask, Response, stream_with_context, render_template, request, redirect, url_for, session, flash
from passlib.hash import pbkdf2_sha256
from datetime import datetime  # Add this at the top of the file
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Secret key for session management

# Paths to JSON files
PRODUCTS_FILE = "data/products.json"
NOTES_FILE = "data/notes.json"
USERS_FILE = "data/users.json"
COMPOSITIONS_FILE = "data/compositions.json"
RANGES_FILE = "data/ranges.json"
DOCUMENTS_FILE = "static/documents"
ALLOWED_IMG_EXTENSIONS={'png'}
ALLOWED_DOC_EXTENSIONS={'pdf', 'SLDPRT'}

app.config['DOCUMENTS_FILE'] = DOCUMENTS_FILE

# In-memory data storage
products = []
notes = []
compositions = []
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
    with open(RANGES_FILE, 'w') as f:
        json.dump(ranges, f, indent=4)

def load_data():
    """Load data from JSON files."""
    global products, notes, compositions, ranges
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

        # Get product image
        base_ref = product['ref'].split('_')[0]
        product['image_path'] = DOCUMENTS_FILE+f"/{base_ref}/Model.png"

        # Get range name
        range_name = next((r['name'] for r in ranges if r['id'] == product['id_range']), "Unknown")
        
        # Get notes for the product
        related_notes = [n['name'] for n in notes if n['id'] in product.get('ids_note', [])]
        
        # Get compositions for the product
        related_compositions = [c['name'] for c in compositions if c['id'] in product.get('ids_composition', [])]
        
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
    """Export products.json into a CSV file with specific transformations."""
    # Define the output CSV columns
    csv_columns = ['ID', 'Reference', 'Name', 'Description', 'Format', 'Cost', 'Range', 'Notes', 'Compositions', 'Persons in Charge', 'Status', 'Start Date']

    # Prepare CSV rows
    csv_rows = []
    for product in products:
        # Get range name
        range_name = next((r['name'] for r in ranges if r['id'] == product['id_range']), "Unknown")

        # Get notes names
        notes_names = ', '.join([n['name'] for n in notes if n['id'] in product.get('ids_note', [])])

        # Get compositions names
        compositions_names = ', '.join([c['name'] for c in compositions if c['id'] in product.get('ids_composition', [])])

        # Get persons in charge
        persons_in_charge = ', '.join(product.get('persons_in_charge', []))

        # Add the row
        csv_rows.append({
            'ID': product['id'],
            'Reference': product['ref'],
            'Name': product['name'],
            'Description': product['description'],
            'Format': product['format'],
            'Cost': product['cost'],
            'Range': range_name,
            'Notes': notes_names,
            'Compositions': compositions_names,
            'Persons in Charge': persons_in_charge,
            'Status': product['status'],
            'Start Date': product['start_date']
        })

    # Generate the CSV response
    def generate_csv():
        # Write the headers
        yield ';'.join(csv_columns) + '\n'
        # Write the data rows
        for row in csv_rows:
            yield ';'.join([str(row[col]) for col in csv_columns]) + '\n'

    # Return the response
    return Response(
        stream_with_context(generate_csv()),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=products.csv"}
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
    related_notes = [n['name'] for n in notes if n['id'] in product.get('ids_note', [])]

    # Retrieve related compositions
    related_compositions = [c['name'] for c in compositions if c['id'] in product.get('ids_composition', [])]

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
        format = request.form['format']
        range_id = int(request.form['range'])

        # Retrieve range name
        range_name = next((r['name'] for r in ranges if r['id'] == range_id), "Unknown")

        # Generate the ref field
        ref = f"FP{range_name[0].upper()}{''.join(word[0].upper() for word in name.split())}_1"

        # Handle notes
        selected_notes = request.form.getlist('notes')
        new_notes = request.form.getlist('new_notes')
        ids_notes = []
        for note_name in new_notes:
            if note_name.strip():
                new_note_id = len(notes) + 1
                notes.append({'id': new_note_id, 'name': note_name})
                ids_notes.append(new_note_id)
        for note_id in selected_notes:
            ids_notes.append(int(note_id))

        # Handle compositions
        selected_compositions = request.form.getlist('compositions')
        new_compositions = request.form.getlist('new_compositions')
        ids_composition = []
        for composition_name in new_compositions:
            if composition_name.strip():
                new_composition_id = len(compositions) + 1
                compositions.append({'id': new_composition_id, 'name': composition_name, 'price': 0.0})  # Default price
                ids_composition.append(new_composition_id)
        for composition_id in selected_compositions:
            ids_composition.append(int(composition_id))


        # Calculate cost based on selected compositions
        cost = sum(comp['price'] for comp in compositions if comp['id'] in ids_composition)

        # Get today's date in JJ/MM/AAAA format
        start_date = datetime.now().strftime("%d/%m/%Y")

        # Handle persons in charge
        persons_in_charge = [p.strip() for p in request.form['persons_in_charge'].split(',') if p.strip()]

        # Extract the base reference for folder naming
        base_ref = ref.split('_')[0]
        product_folder = os.path.join(app.config['DOCUMENTS_FILE'], base_ref)

        # Ensure the folder exists
        os.makedirs(product_folder, exist_ok=True)

        # Handle image upload
        image_file = request.files.get('image')
        if image_file:
            filename = "Model.png"  # Fixed name for product images
            image_path = os.path.join(product_folder, filename)  # Full path to save the image
            try:
                image_file.save(image_path)  # Save the image to the product folder
                flash(f"Image uploaded successfully for {name}.")
            except Exception as e:
                flash(f"Error uploading image: {str(e)}")
                return redirect(request.url)  # Redirect back on error
        else:
            flash("No valid image file provided or invalid file type (only PNG is allowed).")

        image_path = "static/documents/"+base_ref+"/Model.png"
        botol_path = "static/documents/"+base_ref+"/botol.SLDPRT"
        SDS_path = "static/documents/"+base_ref+"/SDS.pdf"

        # Add product to the database
        products.append({
            'id': product_id,
            'name': name,
            'description': description,
            'format': format,
            'cost': cost,
            'id_range': range_id,
            'ids_note': ids_notes,
            'ids_composition': ids_composition,
            'ref': ref, 
            'status':"Initial", 
            "start_date":start_date,
            'persons_in_charge': persons_in_charge,
            "image_path": image_path,
            "botol_path": botol_path,
            "SDS_path": SDS_path
        })

        save_data()  # Save the updated data
        flash(f"Product {name} added successfully!")
        return redirect(url_for('index'))

    return render_template('add_product.html', notes=notes, compositions=compositions, ranges=ranges)

@app.route('/product/update/<int:product_id>', methods=['GET', 'POST'])
def update_product(product_id):
    """Update a product's details."""
    # Ensure proper authorization
    if (
        session.get('type') not in ['manager', 'admin'] and
        session.get('username') not in product.get('persons_in_charge', [])
    ):
        flash("You do not have permission to update this product.")
        return redirect(url_for('index'))

    # Find the product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash("Product not found.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Log the current state of the product before modification
         # Log the current state of the product before modification
        previous_state = get_product_info(product)

        # Update product details
        product['name'] = request.form['name']
        product['description'] = request.form['description']
        product['format'] = request.form['format']
        product['id_range'] = int(request.form['range'])

        product['persons_in_charge'] = [p.strip() for p in request.form['persons_in_charge'].split(',') if p.strip()]

        # Update notes
        selected_notes = request.form.getlist('notes')
        new_notes = request.form.getlist('new_notes')
        note_ids = []
        for note_name in new_notes:
            if note_name.strip():
                new_note_id = len(notes) + 1
                notes.append({'id': new_note_id, 'name': note_name})
                note_ids.append(new_note_id)
        for note_id in selected_notes:
            note_ids.append(int(note_id))

        product['ids_note'] = note_ids

        # Update compositions
        selected_compositions = request.form.getlist('compositions')
        new_compositions = request.form.getlist('new_compositions')
        composition_ids = []
        for composition_name in new_compositions:
            if composition_name.strip():
                new_composition_id = len(compositions) + 1
                compositions.append({'id': new_composition_id, 'name': composition_name, 'price': 0.0})  # Default price
                composition_ids.append(new_composition_id)
        for composition_id in selected_compositions:
            composition_ids.append(int(composition_id))

        # Update product with new compositions
        product['ids_composition'] = composition_ids
        # Recalculate cost
        composition_ids = product.get('ids_composition', [])
        product['cost'] = sum(c['price'] for c in compositions if c['id'] in composition_ids)

        # Update the reference
        update_product_ref(product)

        # Add to history
        if 'history' not in product:
            product['history'] = []
        product['history'].append({
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "modified_by": session['username'],
            "comment": request.form.get('comment', '').strip(),
            "previous_state": previous_state
        })

        save_data()
        flash("Product updated successfully.")
        return redirect(url_for('product_detail', product_id=product_id))

    # Fetch range names and related notes/compositions
    related_notes = product.get('ids_note', [])
    related_compositions = product.get('ids_composition', [])

    return render_template(
        'update_product.html',
        product=product,
        ranges=ranges,
        notes=notes,
        compositions=compositions,
        related_notes=related_notes,
        related_compositions=related_compositions
    )

@app.route('/product/update_status/<int:product_id>', methods=['POST'])
def update_product_status(product_id):
    """Update the status of a product."""
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash("Product not found.")
        return redirect(url_for('index'))

    if session.get('type') not in ['manager', 'admin'] and session.get('username') not in product.get('persons_in_charge', []):
        flash("You do not have permission to update this product's status.")
        return redirect(url_for('index'))

    action = request.form.get('action')
    previous_status = product['status']
    new_status = None

    # Define the status transitions
    if action == "to_to_be_validated" and previous_status == "In progress":
        new_status = "To be validated"
    elif action == "to_done" and previous_status == "To be validated":
        new_status = "Done"
    elif action == "to_in_progress" and previous_status in ["Initial", "To be validated", "Done", "Archived"]:
        new_status = "In progress"
    elif action == "archive":
        new_status = "Archived"

    if new_status:
        previous_state = get_product_info(product)
        product['status'] = new_status

        if 'history' not in product:
            product['history'] = []
        product['history'].append({
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "modified_by": session['username'],
            "comment": f"Status update: {previous_status} --> {new_status}",
            "previous_state": previous_state
        })
        save_data()
        flash(f"Product status updated to '{new_status}' successfully.")
    else:
        flash("Invalid status transition.")

    return redirect(url_for('index'))


@app.route('/product/validate_status/<int:product_id>', methods=['GET', 'POST'])
def validate_product_status(product_id):
    """Validate or revert the product's status."""
    # Find the product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash("Product not found.")
        return redirect(url_for('index'))

    # Ensure proper authorization
    if session.get('type') not in ['manager', 'admin']:
        flash("You do not have permission to validate this product.")
        return redirect(url_for('index'))

    previous_state = get_product_info(product)

    if request.method == 'POST':
        # Determine the new status
        action = request.form['action']
        previous_status = product['status']
        if action == "done":
            new_status = "Done"
        elif action == "revert":
            new_status = "In progress"
        else:
            flash("Invalid action.")
            return redirect(url_for('index'))

        # Update the status
        product['status'] = new_status

        # Add to history
        if 'history' not in product:
            product['history'] = []
        additional_comment = request.form.get('comment', '').strip()
        product['history'].append({
            "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "modified_by": session['username'],
            "comment": f"Status update: {previous_status} --> {new_status}" + (f". Additional comment: {additional_comment}" if additional_comment else ""),
            "previous_state": previous_state
        })

        save_data()
        flash(f"Product status updated to '{new_status}' successfully.")
        return redirect(url_for('index'))

    return render_template(
        'validate_status.html',
        product=product
    )

@app.route('/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """Delete or archive a product based on its current status."""
    # Find the product
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        flash("Product not found.")
        return redirect(url_for('index'))

    # Ensure only admins can delete products
    if session.get('type') != 'admin':
        flash("You do not have permission to delete this product.")
        return redirect(url_for('index'))

    # Check action
    action = request.form.get('action', '')
    if action == "delete":
        if product['status'] != "Archived":
            flash("Only archived products can be deleted.")
            return redirect(url_for('index'))

        # Remove product permanently
        products.remove(product)
        save_data()
        flash("Product deleted permanently.")
    else:
        flash("Invalid action.")

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

def get_product_info(product):
    return {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "format": product["format"],
            "cost": product["cost"],
            "id_range": product["id_range"],
            "ref": product["ref"],
            "status": product["status"],
            "start_date": product["start_date"],
            "ids_composition": list(product.get("ids_composition", [])),
            "ids_note": list(product.get("ids_note", [])),
            "persons_in_charge": list(product.get("persons_in_charge", []))
        }

def update_product_ref(product):
    ref_parts = product['ref'].rsplit('_', 1)
    if len(ref_parts) == 2 and ref_parts[1].isdigit():
        product['ref'] = f"{ref_parts[0]}_{int(ref_parts[1]) + 1}"
    else:
        product['ref'] = f"{product['ref']}_"

def allowed_file(filename, file_type):
    if (file_type == 'img'):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG_EXTENSIONS
    elif (file_type == 'doc'):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS
    return False

if __name__ == '__main__':
    app.run(debug=True)