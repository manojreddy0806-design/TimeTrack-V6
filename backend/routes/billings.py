# backend/routes/billings.py
from flask import Blueprint, request, jsonify, g
from ..models import get_billings_by_stores, update_billing_payment, get_stores, StoreBilling, get_all_managers, get_current_billing_month
from ..auth import require_auth

bp = Blueprint("billings", __name__)

@bp.get("/")
@require_auth(roles=['manager', 'super-admin'])
def get_billings():
    """Get all billings grouped by store for managers (current month only)"""
    try:
        tenant_id = g.tenant_id
        current_month = get_current_billing_month()
        
        # Get all stores for this tenant
        stores = get_stores(tenant_id=tenant_id)
        store_names = [store["name"] for store in stores]
        
        # Get billings grouped by store (for current month)
        billings = get_billings_by_stores(tenant_id, billing_month=current_month)
        
        # Ensure all stores have billing entries (even if empty)
        for store_name in store_names:
            if store_name not in billings:
                billings[store_name] = {
                    'electricity': {'paid': False, 'amount': 0},
                    'wifi': {'paid': False, 'amount': 0},
                    'gas': {'paid': False, 'amount': 0}
                }
        
        return jsonify({
            'stores': store_names,
            'billings': billings,
            'billing_month': current_month
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get billings: {str(e)}"}), 500


@bp.post("/pay")
@require_auth(roles=['manager', 'super-admin'])
def pay_billing():
    """Record a payment for a billing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        store_id = data.get("store_id")
        if not store_id:
            return jsonify({"error": "store_id is required"}), 400
        
        bill_type = data.get("bill_type")
        if not bill_type:
            return jsonify({"error": "bill_type is required"}), 400
        
        if bill_type.lower() not in ['electricity', 'wifi', 'gas']:
            return jsonify({"error": "bill_type must be 'electricity', 'wifi', or 'gas'"}), 400
        
        amount = data.get("amount")
        if amount is None:
            return jsonify({"error": "amount is required"}), 400
        
        try:
            amount = float(amount)
            if amount < 0:
                return jsonify({"error": "amount must be positive"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "amount must be a valid number"}), 400
        
        tenant_id = g.tenant_id
        
        # Verify store belongs to tenant
        stores = get_stores(tenant_id=tenant_id)
        store_names = [store["name"] for store in stores]
        if store_id not in store_names:
            return jsonify({"error": f"Store '{store_id}' not found"}), 404
        
        # Update billing payment
        billing = update_billing_payment(tenant_id, store_id, bill_type, amount)
        
        return jsonify(billing), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to record payment: {str(e)}"}), 500


@bp.get("/managers")
@require_auth(roles=['super-admin'])
def get_managers_billings():
    """Get all managers with their stores' billing information for super admin"""
    try:
        tenant_id = g.tenant_id
        current_month = get_current_billing_month()
        
        # Get all managers (exclude super admin)
        all_managers = get_all_managers(tenant_id=tenant_id)
        managers = [m for m in all_managers if not m.get('is_super_admin', False)]
        
        # Get billings for all stores
        all_billings = get_billings_by_stores(tenant_id, billing_month=current_month)
        
        # Group stores by manager and attach billing info
        managers_with_billings = []
        for manager in managers:
            manager_username = manager['username']
            
            # Get stores for this manager
            stores = get_stores(tenant_id=tenant_id, manager_username=manager_username)
            
            # Get billing info for each store
            stores_with_billings = []
            total_paid = 0
            total_unpaid = 0
            
            for store in stores:
                store_name = store['name']
                store_billing = all_billings.get(store_name, {
                    'electricity': {'paid': False, 'amount': 0},
                    'wifi': {'paid': False, 'amount': 0},
                    'gas': {'paid': False, 'amount': 0}
                })
                
                # Calculate totals
                for bill_type in ['electricity', 'wifi', 'gas']:
                    bill = store_billing.get(bill_type, {'paid': False, 'amount': 0})
                    if bill['paid']:
                        total_paid += bill['amount']
                    else:
                        # Count unpaid bills
                        total_unpaid += 1
                
                stores_with_billings.append({
                    'name': store_name,
                    'billing': store_billing
                })
            
            managers_with_billings.append({
                'id': manager['id'],
                'name': manager['name'],
                'username': manager['username'],
                'stores': stores_with_billings,
                'stores_count': len(stores_with_billings),
                'total_paid': total_paid,
                'unpaid_bills_count': total_unpaid
            })
        
        return jsonify({
            'managers': managers_with_billings,
            'billing_month': current_month
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get managers billings: {str(e)}"}), 500


@bp.get("/manager/<manager_username>")
@require_auth(roles=['super-admin'])
def get_manager_billings(manager_username):
    """Get billing details for a specific manager's stores"""
    try:
        tenant_id = g.tenant_id
        current_month = get_current_billing_month()
        
        # Get stores for this manager
        stores = get_stores(tenant_id=tenant_id, manager_username=manager_username)
        
        if not stores:
            return jsonify({"error": "No stores found for this manager"}), 404
        
        # Get billings for these stores
        all_billings = get_billings_by_stores(tenant_id, billing_month=current_month)
        
        # Format store billings
        stores_with_billings = []
        for store in stores:
            store_name = store['name']
            store_billing = all_billings.get(store_name, {
                'electricity': {'paid': False, 'amount': 0},
                'wifi': {'paid': False, 'amount': 0},
                'gas': {'paid': False, 'amount': 0}
            })
            
            stores_with_billings.append({
                'name': store_name,
                'billing': store_billing
            })
        
        # Get manager info
        from ..models import get_manager_by_username
        manager = get_manager_by_username(manager_username, tenant_id=tenant_id)
        if not manager:
            return jsonify({"error": "Manager not found"}), 404
        
        return jsonify({
            'manager': {
                'name': manager['name'],
                'username': manager['username']
            },
            'stores': stores_with_billings,
            'billing_month': current_month
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to get manager billings: {str(e)}"}), 500

