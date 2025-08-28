# Vendor Management System - Fixed Version

A working vendor management system with proper template structure and simplified functionality.

## Features

- **Multi-Role Authentication**: Admin, Manager, and Vendor roles
- **Attendance Tracking**: Mark and view attendance with calendar interface
- **Manager Approval**: Managers can approve or reject vendor attendance
- **Admin Management**: User management and system administration
- **Responsive UI**: Bootstrap-based responsive design

## Installation

1. **Extract the files**:
   ```bash
   # Files are already extracted in vendor_management_system_fixed/
   cd vendor_management_system_fixed
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start MongoDB**:
   Make sure MongoDB is running on your system.

5. **Initialize database**:
   ```bash
   python init_db.py
   ```

6. **Start the application**:
   ```bash
   python app.py
   ```

7. **Access the application**:
   Open your browser and go to `http://localhost:5000`

## Default Login Credentials

- **Admin**: admin1 / password123
- **Manager**: manager1 / password123  
- **Vendor**: vendor1 / password123
- **Vendor**: vendor2 / password123

## Project Structure

```
vendor_management_system_fixed/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── init_db.py            # Database initialization
├── README.md             # This file
├── app/
│   ├── models/           # Database models
│   ├── routes/           # Route handlers
│   ├── utils/            # Utility functions
│   ├── templates/        # HTML templates
│   │   ├── auth/         # Authentication pages
│   │   ├── vendor/       # Vendor interface
│   │   ├── manager/      # Manager interface
│   │   ├── admin/        # Admin interface
│   │   └── errors/       # Error pages
│   └── static/           # CSS, JS, uploads
├── config/               # Configuration files
└── data/                 # Sample data files
```

## Key Features

### For Vendors
- Mark daily attendance with multiple status options
- View attendance calendar with color-coded status
- Track monthly attendance summary
- View attendance history

### For Managers
- Review and approve team attendance
- View team performance dashboard
- Manage team data and generate reports

### For Administrators
- Complete user management (add, edit, deactivate users)
- System monitoring and statistics
- Data upload and management capabilities
- Generate system-wide reports

## Technical Details

- **Backend**: Python Flask with modular architecture
- **Database**: MongoDB with proper indexing
- **Frontend**: Bootstrap 5 with custom styling
- **Authentication**: Session-based with role management

## Troubleshooting

1. **MongoDB Connection Issues**:
   - Ensure MongoDB is running: `mongod` or `brew services start mongodb-community`
   - Check MongoDB status: `ps aux | grep mongod`

2. **Template Not Found Errors**:
   - This fixed version includes all required templates
   - Templates are properly configured in `app.py`

3. **Permission Issues**:
   - Make sure you have proper permissions to create files in the project directory
   - On Linux/Mac, you might need to run with appropriate permissions

## Development Notes

This is a simplified but fully functional version of the vendor management system. It includes:

- ✅ All required templates
- ✅ Proper Flask configuration
- ✅ Working authentication
- ✅ Database models and operations
- ✅ Responsive UI with Bootstrap
- ✅ Error handling

Future enhancements can include:
- Advanced mismatch detection
- File upload functionality
- Email notifications
- Advanced reporting
- Audit workflows

## Support

If you encounter any issues:
1. Check that MongoDB is running
2. Verify all dependencies are installed
3. Ensure you're running from the correct directory
4. Check the console for any error messages

The application should now run without template errors and provide a complete working vendor management system.
