Here are the features implemented in your application so far:
Authentication and Authorization

    User Login and Registration:
        Users can register with a username and password.
        Passwords are securely hashed and stored in a JSON file.
        Registered users can log in using their credentials.

    Role-Based Access Control:
        Users are assigned one of the following roles: admin, manager, or user.
        Access to certain features and routes is restricted based on the user's role.

    Session Management:
        Logged-in users have their session tracked using Flask sessions.
        Users can log out, which clears their session data.

Product Management

    View Products:
        All users can view a table of products with details such as:
            Range
            Product Name
            Format
            Retail Price
            Cost
            Quantity
            Notes
            Compositions
            Description

    Add Products:
        Only users with admin or manager roles can add new products.
        Admins and managers can:
            Set the product's range, price, cost, format, and quantity.
            Add related notes and compositions to the product.

    Edit Product Details:
        Quantity: Editable by all users.
        Retail Price and Cost: Editable only by users with admin or manager roles.
        Inline editing is available in the product table, as well as in the product detail page.

    Delete Products:
        Only admin users can delete products.
        If logged in as an admin, the "Action" column in the product table displays a delete button.

User Management

    Admin-Only User Management Page:
        Admins have access to a dedicated page to manage user accounts.
        The page lists all registered users and their roles.

    Update User Roles:
        Admins can change a user's role to user, manager, or admin.
        Role changes are immediately saved to the database.

    Delete Users:
        Admins can delete user accounts from the system.
        Admins cannot delete their own account.

Additional Features

    Dynamic Table Filtering and Sorting:
        Users can filter the product table by:
            Range
            Product Name
            Notes
            Compositions
            Format
            Price Range
        Users can sort the table columns in ascending or descending order for fields like:
            Range
            Product Name
            Retail Price
            Cost
            Quantity

    Export to CSV:
        Users can export the filtered and sorted product table as a CSV file.
        The CSV includes fields like Range, Product Name, Format, Retail Price, Cost, Notes, and Compositions.

    Responsive Interface:
        The application provides an intuitive user interface with forms for adding and editing products.
        Forms and tables dynamically adapt based on the user's role.

Security Features

    Password Hashing:
        Passwords are hashed using a secure hashing algorithm before being stored.

    Role Validation:
        Unauthorized access to certain routes and features is blocked with appropriate flash messages.

    Self-Protection:
        Admins cannot delete their own accounts to prevent accidental lockouts.
