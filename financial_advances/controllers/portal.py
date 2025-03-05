from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import format_amount, float_compare


class CustomerPortalExtended(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        print('values:', values)
        if 'farmer_count' in counters:
            partner = request.env.user.partner_id
            values['farmer_count'] = 1
        
        return values
    
# class FinancialAdvancesController(http.Controller):
#     @http.route(['/my/financial'], type='http', auth="user", website=True)
#     def portal_my_financial(self):
#         farmer = request.env.user.partner_id
#         advances = request.env['farmers.financial.advances'].sudo().search([
#             ('farmer_id', '=', farmer.id)
#         ])

#         # Existing calculations
#         total_paid = total_unpaid = receipt_count = 0
#         payment_breakdown = []

#         # New calculations
#         total_deductions = 0
#         total_sales = 0
#         total_expenses = 0

#         # Calculate financial advance totals
#         for advance in advances:
#             for installment in advance.installment_ids:
#                 # Existing payment logic
#                 # ...
                
#                 # Add deductions
#                 total_deductions += installment.deduction_amount
#                 payment_breakdown.append({
#                     # Existing fields...
#                     'deduction': installment.deduction_amount
#                 })

#         # Calculate sales from sale orders
#         sale_orders = request.env['sale.order'].sudo().search([
#             ('partner_id', '=', farmer.id),
#             ('state', 'in', ['sale', 'done'])
#         ])
#         total_sales = sum(order.amount_total for order in sale_orders)

#         # Calculate expenses from vendor bills
#         vendor_bills = request.env['account.move'].sudo().search([
#             ('partner_id', '=', farmer.id),
#             ('move_type', '=', 'in_invoice'),
#             ('payment_state', '=', 'paid')
#         ])
#         total_expenses = sum(bill.amount_total for bill in vendor_bills)

#         # Calculate net balance
#         net_balance = (total_sales + total_paid) - (total_expenses + total_deductions)

#         return request.render('financial_advances.portal_my_financial', {
#             # Existing values...
#             'total_deductions': total_deductions,
#             'total_sales': total_sales,
#             'total_expenses': total_expenses,
#             'net_balance': net_balance,
#         })

class FinancialAdvancesController(CustomerPortal):
    @http.route(['/my/financial'], type='http', auth="user", website=True)
    def portal_my_financial(self, **kw):
        # Get the current user's partner
        partner = request.env.user.partner_id
        total_quantity_recipe, total_quantity_demand, remaining_quantity = self.stock_picking_advance(partner)
        total_paid, total_not_paid, advance_amount_total = self.farmer_financial_advance(partner)
        total_amount, total_amount_paid, total_amount_unpaid = self.account_bill_advance(partner)
        
        values = self._prepare_portal_layout_values()
        values.update({
            "advance_amount_total": advance_amount_total,
            'total_paid': total_paid,
            'total_not_paid': total_not_paid,
            'receipt_quantity_total': total_quantity_recipe,
            "total_quantity_demand": total_quantity_demand,
            "remaining_quantity": remaining_quantity,
            'page_name': 'financial',
            'format_amount': self._format_amount_with_currency,
            'total_amount': total_amount,
            'total_amount_paid': total_amount_paid,
            'total_amount_unpaid': total_amount_unpaid,
        })
        
        return request.render('financial_advances.portal_my_financial', values)
    
    @http.route(['/my/financial/advance/<int:advance_id>'], type='http', auth="user", website=True)
    def portal_my_financial_advance(self, advance_id, **kw):
        advance = request.env['farmers.financial.advances'].sudo().browse(advance_id)
        
        # Security check
        if not advance or advance.farmer_id != request.env.user.partner_id:
            return request.redirect('/my/financial')
        
        # Calculate paid and remaining amounts
        advance_paid_amount = sum(advance.installment_ids.filtered(
            lambda i: i.account_move_state == 'posted').mapped('installment_amount'))
        advance_remaining_amount = advance.advance_amount - advance_paid_amount
        
        # Calculate payment progress percentage
        payment_progress = 0
        if advance.advance_amount > 0:
            payment_progress = round((advance_paid_amount / advance.advance_amount) * 100)
        
        # Get deductions related to this specific advance
        advance_deductions = self._get_advance_deductions(advance)
        
        values = self._prepare_portal_layout_values()
        values.update({
            'advance': advance,
            'advance_paid_amount': advance_paid_amount,
            'advance_remaining_amount': advance_remaining_amount,
            'payment_progress': payment_progress,
            'advance_deductions': advance_deductions,
            'page_name': 'financial_advance',
            'format_amount': self._format_amount_with_currency,
        })
        
        return request.render('financial_advances.portal_my_financial_advance', values)
    
    def _format_amount_with_currency(self, amount, currency=None):
        if currency is None:
            currency = request.env.company.currency_id
        return format_amount(request.env, amount, currency)
    
    def stock_picking_advance(self,partner):
        all_recipped = request.env['stock.picking'].sudo().search([
            ('partner_id', '=', partner.id),
            ('picking_type_code', '=', 'incoming'),
        ])
        total_quantity_demand = 0
        total_quantity_recipe = 0
        for rec in all_recipped:
            
            all_move_line = rec.move_ids_without_package
            for move_line in all_move_line:
                total_quantity_demand += move_line.product_uom_qty
                total_quantity_recipe += move_line.quantity
        remaining_quantity = total_quantity_demand - total_quantity_recipe
        total_quantity_recipe = f"{total_quantity_recipe} Kg"
        total_quantity_demand = f"{total_quantity_demand} Kg"
        remaining_quantity = f"{remaining_quantity} Kg"
        return total_quantity_recipe, total_quantity_demand, remaining_quantity
    
    def farmer_financial_advance(self,partner):
        # Fetch all installments for this farmer's advances
        advances = request.env['farmers.financial.advances'].sudo().search([
            ('farmer_id', '=', partner.id)
        ])
        
        total_paid = 0
        advance_amount_total = 0
        # total_pay=f"Pay : {total_pay} / {record.advance_amount}, Remaining : {record.advance_amount - total_pay}"
        for advance in advances:
            total_pay_split = advance.total_pay.split('/')
            total_paid += float(total_pay_split[0].split(':')[1].strip())
            advance_amount_total += advance.advance_amount
        total_not_paid = advance_amount_total - total_paid
        return total_paid, total_not_paid, advance_amount_total
    
    def account_bill_advance(self,partner):
        all_bills = request.env['account.move'].sudo().search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'in_invoice'),
            
        ])
        total_amount = 0
        total_amount_paid = 0 # 'paid,partially_paid'
        total_amount_unpaid = 0 # 'not_paid,un_payment'
        for bill in all_bills:
            total_amount += bill.amount_total
            if bill.payment_state in ['paid', 'partially_paid']:
                total_amount_paid += bill.amount_total
            elif bill.payment_state in ['not_paid', 'in_payment']:
                total_amount_unpaid += bill.amount_total
        return total_amount, total_amount_paid, total_amount_unpaid
    

    
    def _get_farmer_sales(self, partner):
        """
        Get all sales for this farmer.
        Implement based on your sales model structure.
        """
        # This is a placeholder implementation
        # You should replace this with your actual implementation based on your sales model
        
        # Example:
        # return request.env['sale.order.line'].sudo().search([
        #     ('order_id.partner_id', '=', partner.id),
        #     ('order_id.state', 'in', ['sale', 'done']),
        # ], order='date desc')
        
        return request.env['sale.order.line'].sudo().search([])[:0]  # Empty recordset as placeholder
    
    def _get_farmer_deductions(self, partner):
        """
        Get all deductions for this farmer.
        Implement based on your deduction model structure.
        """
        # This is a placeholder implementation
        # You should replace this with your actual implementation based on your deduction model
        
        # Example:
        # return request.env['your.deduction.model'].sudo().search([
        #     ('partner_id', '=', partner.id),
        # ], order='date desc')
        
        return request.env['account.move.line'].sudo().search([])[:0]  # Empty recordset as placeholder
    
    def _get_advance_deductions(self, advance):
        """
        Get deductions specifically related to a particular advance.
        Implement based on your deduction model structure.
        """
        # This is a placeholder implementation
        # You should replace this with your actual implementation
        
        # Example:
        # return request.env['your.deduction.model'].sudo().search([
        #     ('advance_id', '=', advance.id),
        # ], order='date desc')
        
        return request.env['account.move.line'].sudo().search([])[:0]
  