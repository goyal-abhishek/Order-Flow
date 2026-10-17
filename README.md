# 🍽️ Order Management App

A simple Flask + SQLite restaurant order management system for creating, tracking, and managing restaurant orders with role-based access.

## Features

- 🔐 Role-based login system
- 👑 Admin and Staff roles
- 📞 10-digit customer phone number validation
- 📍 Store customer addresses
- 🔒 Staff cannot view customer phone numbers or addresses
- Order types: Dine-In, Takeaway, Delivery
- Order lifecycle: Created → Confirmed → Preparing → Ready → Served → Paid → Completed
- ➕ Create new orders
- ✏️ Edit existing orders
- ⏭️ Advance orders through their lifecycle
- 🔎 Filter orders by status
- 🗑️ Delete any order
- 📅 Orders displayed chronologically
- 🔢 Order numbers automatically rearrange after deletion
- 💾 SQLite database
- 🔄 Automatic database upgrade for older databases
- 📊 Responsive dashboard

## User Roles

| Role | Access |
|------|--------|
| **Admin** | Full order management + customer phone & address |
| **Staff** | Order management without customer phone & address |

## Order Lifecycle

```text
Created → Confirmed → Preparing → Ready → Served → Paid → Completed