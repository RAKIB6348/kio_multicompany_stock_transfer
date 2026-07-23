# KIO Multi-Company Stock Transfer

**Version:** 17.0.1.0.0  
**License:** LGPL-3  
**Category:** Inventory/Inventory  
**Author:** Rakib Hasan

## Module Overview

KIO Multi-Company Stock Transfer is an Odoo 17 module that manages stock transfers between two different companies operating within the same Odoo database. The module provides a complete inter-company logistics workflow with route configuration, multi-company security, and automated stock movement creation.

## Business Purpose

Organizations operating multiple companies in a single Odoo database need to transfer inventory between locations belonging to different legal entities. This module provides:

- Centralized configuration of transfer routes between companies
- Automated creation of source pickings and destination receipts
- Shared transit location for inter-company stock movement
- Multi-company security with proper access controls
- Complete audit trail via Odoo's chatter system

## Important Limitations

**This module does NOT:**

- Create Sales Orders
- Create Purchase Orders
- Create Invoices or Vendor Bills
- Manually create Accounting Entries
- Modify standard Odoo stock valuation behavior

Standard Odoo stock valuation remains active. The module only manages stock transfer logistics between companies.

## Workflow Overview

### 1. Route Configuration

Before creating transfers, define transfer routes under **Inventory > Configuration > Multi-Company Transfer Routes**.

Each route specifies:
- Source company and warehouse
- Destination company and warehouse
- Shared transit location (no company assigned)
- Source and destination picking types

### 2. Transfer Creation

Create a transfer under **Inventory > Operations > Multi-Company Stock Transfers**:
1. Select a pre-configured route
2. Add transfer lines with products and quantities
3. Set scheduled date and responsible user
4. Click **Confirm**

### 3. Source Company Dispatch

When confirmed:
- Source picking is created in the source company
- Source location: Source warehouse main stock
- Destination location: Shared transit location
- Stock moves are created for each transfer line
- Picking is confirmed and stock is reserved
- User processes the picking (partial or full)

### 4. Shared Transit Location

- Transit location must have no company assigned
- Stock moves through transit are tracked
- Enables cross-company visibility

### 5. Destination Company Receipt

When source picking is validated (Done):
- Destination receipt is automatically created
- Company: Destination company
- Source location: Shared transit location
- Destination location: Destination warehouse main stock
- Quantities match actual dispatched quantities
- Backorders create additional destination receipts

### 6. Transfer Completion

When destination receipt is validated:
- Transfer state updates to Done
- All quantities are verified
- Complete audit trail available

## Transfer States

| State | Description |
|-------|-------------|
| Draft | Initial state, not yet confirmed |
| Confirmed | Confirmed, source picking created |
| Ready | Source picking assigned/reserved |
| Partially Dispatched | Some quantity dispatched from source |
| In Transit | Stock dispatched, awaiting receipt |
| Partially Received | Some dispatched quantity received |
| Done | All quantities dispatched and received |
| Cancelled | Transfer cancelled |

## Partial Dispatch and Backorders

The module supports partial dispatch with automatic backorder handling:

**Example:**
- Requested: 100 units
- First dispatch: 60 units
  - Backorder created for remaining 40 units
  - Destination receipt created for 60 units
- Second dispatch (backorder): 40 units
  - Second destination receipt created for 40 units

**Rules:**
- Destination receipt quantity cannot exceed dispatched quantity
- Over-receipt is blocked with validation error
- Partial receipts are supported
- Each source dispatch creates its own destination receipt

## Security

### Security Groups

| Group | Permissions |
|-------|------------|
| Multi-Company Stock Transfer User | Read allowed transfers, create requests, edit drafts, open pickings |
| Multi-Company Stock Transfer Manager | Confirm transfers, cancel transfers, configure routes, full access |

Manager group implies User group.

### Multi-Company Access Rules

Record rules ensure users only see transfers related to their allowed companies:

```sql
-- Access when source company is in user's companies
source_company_id IN company_ids

-- OR when destination company is in user's companies
destination_company_id IN company_ids
```

### Access Rights

| Model | User | Manager |
|-------|------|---------|
| kio.multicompany.stock.transfer | Read, Write, Create | Full CRUD |
| kio.multicompany.stock.transfer.line | Read, Write, Create | Full CRUD |
| kio.multicompany.transfer.route | None | Full CRUD |

## Cancellation Rules

| Transfer State | Cancellation | Reason |
|----------------|--------------|--------|
| Draft | Allowed | No stock moved |
| Confirmed | Allowed | If no source picking is Done |
| Ready | Allowed | If no source picking is Done |
| Partially Dispatched | Blocked | Stock has moved |
| In Transit | Blocked | Stock has moved |
| Partially Received | Blocked | Stock has moved |
| Done | Blocked | Stock has moved |
| Cancelled | Blocked | Already cancelled |

**Error message:**
> The transfer cannot be cancelled because stock has already moved. Process a return transfer or stock correction instead.

## Installation

### Prerequisites

- Odoo 17.0
- Stock module
- Mail module

### Steps

1. Place the `kio_multicompany_stock_transfer` directory in your Odoo addons path
2. Restart the Odoo server
3. Go to Settings > Apps
4. Search for "KIO Multi-Company Stock Transfer"
5. Click Install

### Command Line

```bash
./odoo-bin -c odoo.conf -d <database_name> \
  -i kio_multicompany_stock_transfer --stop-after-init
```

## Upgrade

```bash
./odoo-bin -c odoo.conf -d <database_name> \
  -u kio_multicompany_stock_transfer --stop-after-init
```

## User Guide

### Creating a Route

1. Navigate to **Inventory > Configuration > Multi-Company Transfer Routes**
2. Click Create
3. Fill in:
   - Route Name
   - Source Company
   - Source Warehouse
   - Destination Company
   - Destination Warehouse
   - Transit Location (must be shared, no company)
   - Source Picking Type
   - Destination Picking Type
4. Save

### Creating a Transfer

1. Navigate to **Inventory > Operations > Multi-Company Stock Transfers**
2. Click Create
3. Select Route (auto-fills company/warehouse fields)
4. Add product lines with quantities
5. Click Confirm

### Processing a Transfer

1. Open the confirmed transfer
2. Click Source Picking smart button
3. Process the picking (validate with quantities)
4. Destination receipt is automatically created
5. Open destination picking from the transfer
6. Validate the destination receipt
7. Transfer state updates to Done

## Testing Checklist

### Route Validation
- [ ] Valid route between two companies created
- [ ] Same source/destination company rejected
- [ ] Warehouse-company mismatch rejected
- [ ] Company-specific transit location rejected

### Transfer Validation
- [ ] Transfer without lines rejected
- [ ] Zero quantity rejected
- [ ] Source picking created in source company
- [ ] Source picking uses correct locations

### Dispatch and Receipt
- [ ] Destination receipt not created before dispatch
- [ ] Completing source picking creates destination receipt
- [ ] Destination receipt belongs to destination company
- [ ] Receipt quantity equals dispatched quantity
- [ ] Duplicate destination receipt not created
- [ ] Partial dispatch creates receipt for partial quantity
- [ ] Source backorder creates another receipt
- [ ] Over-receipt blocked with error

### Quantities and States
- [ ] Transfer totals correct
- [ ] Transfer states transition correctly

### Cancellation
- [ ] Cancellation before dispatch works
- [ ] Cancellation after dispatch blocked

### Security
- [ ] Source/destination company users can access records
- [ ] Unrelated company user cannot access records

### Code Quality
- [ ] No direct stock.quant manipulation
- [ ] No raw SQL

## Troubleshooting

### Issue: Cannot confirm transfer

**Possible causes:**
- User not in Manager group
- No transfer lines added
- Route not configured

**Solution:**
- Verify user has Manager group
- Add at least one transfer line
- Check route configuration

### Issue: Destination receipt not created

**Possible causes:**
- Source picking not validated
- No moves with quantity_done > 0

**Solution:**
- Validate source picking
- Ensure at least one move has completed quantity

### Issue: Over-receipt validation error

**Possible causes:**
- Receipt quantity exceeds dispatched quantity

**Solution:**
- Set receipt quantity equal to or less than dispatched quantity
- Create backorder for remaining quantity

### Issue: Cannot cancel transfer

**Possible causes:**
- Transfer is in Done state
- Source picking is already Done

**Solution:**
- Process return transfer or stock correction
- Cancel before dispatch completes

## Known Limitations

1. **No Financial Integration:** The module does not create invoices, bills, or accounting entries
2. **No Sales/Purchase Orders:** Transfers are initiated directly, not from SO/PO
3. **Single Route per Transfer:** Each transfer uses one route only
4. **Manual Stock Adjustment:** Returns require manual stock adjustments
5. **Transit Location Requirement:** Must have a shared transit location (no company)
6. **Company-Specific Warehouses:** Source and destination warehouses must belong to their respective companies

## Technical Details

### Models

| Model | Description |
|-------|-------------|
| `kio.multicompany.stock.transfer` | Main transfer record |
| `kio.multicompany.stock.transfer.line` | Transfer line items |
| `kio.multicompany.transfer.route` | Route configuration |
| `stock.picking` (inherited) | Extended with transfer fields |

### Sequence

- Code: `kio.multicompany.stock.transfer`
- Format: `MCT/YYYY/NNNNN`
- Example: `MCT/2026/00001`

### Dependencies

- `stock` - Core inventory management
- `mail` - Chatter and activity tracking

## License

This module is licensed under LGPL-3.

Copyright (C) 2026 Rakib Hasan
