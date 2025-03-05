from odoo import models, fields, api
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class EmployeeFinancialAdvances(models.Model):
    _name = "employees.financial.advances"
    _description = "Employees Financial Advances"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    employee_id = fields.Many2one("res.partner", string="Employee Name", required=True)
    advance_amount = fields.Float(
        string="Advance Amount",
        help="The amount requested as an advance (maximum 1000 dinars)",
        digits=(10, 2),
        default=0.0,
        required=True,
        domain=[("advance_amount", "<=", 1000)],
    )
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id, required=True)
    num_installments = fields.Integer(
        string="Number of Installments (Months)",
        help="The number of months over which the advance will be repaid (maximum 6 months)",
        default=1,
        required=True,
        domain=[("num_installments", ">=", 1), ("num_installments", "<=", 6)],
    )
    installment_value = fields.Float(string="Installment Value (Month)", compute="_compute_installment_value", digits=(10, 2))
    advance_start_date = fields.Date(string="Advance Start Date", required=True)

    advance_end_date = fields.Date(string="Advance End Date", compute="_compute_advance_end_date", default=False)
    installment_ids = fields.One2many(
        "employees.financial.installments",
        "advance_id",
        string="Installments",
    )
    stage = fields.Selection(
        [
            ("draft", "Draft"),
            ("post", "Post"),
        ],
        string="Stage",
        default="draft",
        required=True,
        tracking=1
    )
    # employee = fields.Many2one("hr.employee", string="Employee", compute="_compute_employee", store=True)
    
    @api.depends("advance_start_date", "num_installments")
    def _compute_advance_end_date(self):
        for record in self:
            if record.advance_start_date:
                record.advance_end_date = record.advance_start_date + relativedelta(months=record.num_installments - 1)
            else:
                record.advance_end_date = False

    @api.depends("advance_amount", "num_installments")
    def _compute_installment_value(self):
        for record in self:
            record.installment_value = record.advance_amount / record.num_installments

    @api.constrains("advance_amount", "num_installments")
    def _check_advance_constraints(self):
        for record in self:
            if record.advance_amount > 1000:
                raise ValidationError("Advance amount cannot exceed 1000 dinars.")
            if record.num_installments < 1 or record.num_installments > 6:
                raise ValidationError("Number of installments must be between 1 and 6 months.")

    # @api.depends("employee_id")
    # def _compute_employee(self):
    #     for record in self:
    #         print(record.employee_id)
    #         record.employee = record.employee_id.employee_id
    # @api.model
    # def create(self, vals):
    #     # after create create new EmployeeFinancialInstallment start date is 01/01/2022 and end date is 01/06/2022
    #     # loop in range of num_installments and create new EmployeeFinancialInstallment
    #     # with installment_date = advance_start_date + i month
    #     # and installment_amount = installment_value
    #     # description = "Installment of' + installment_date
    #     record = super(EmployeeFinancialAdvances, self).create(vals)

        
    #     return record

    def write(self, vals):
        # if advance_amount or num_installments is updated, update the installment_value
        # and update the EmployeeFinancialInstallment records
        res = super(EmployeeFinancialAdvances, self).write(vals)
        if "advance_amount" in vals or "num_installments" in vals :
            for record in self:
                if record.stage == "post":
                    # remove all installments and create new ones
                    record.env["employees.financial.installments"].search([("advance_id", "=", record.id)]).unlink()
                    for i in range(record.num_installments):
                        sum_date = record.advance_start_date + relativedelta(months=i)
                        record.env["employees.financial.installments"].create(
                            {
                                "advance_id": record.id,
                                "description": "Installment of " + str(sum_date),
                                "installment_date": sum_date,
                                "installment_amount": record.installment_value,
                            }
                        )
        return res
    
    def post_employee_financial(self):
        for record in self:
            if record.stage == "draft":
                record.stage = "post"
                for i in range(record.num_installments):
                    sum_date = record.advance_start_date + relativedelta(months=i)
                    record.env["employees.financial.installments"].create(
                        {
                            "advance_id": record.id,
                            "description": "Installment Of " + str(sum_date),
                            "installment_date": sum_date,
                            "installment_amount": record.installment_value,
                        }
                    )


class EmployeeFinancialInstallment(models.Model):
    _name = "employees.financial.installments"
    _description = "Employees Financial Installments"

    advance_id = fields.Many2one("employees.financial.advances", string="Advance ID", required=True, ondelete="cascade")
    description = fields.Char(string="Description", help="Description of the installment", required=True)
    installment_date = fields.Date(string="Installment Date", required=True)
    installment_amount = fields.Float(
        string="Installment Amount (Month)", help="The amount to be paid as an installment", digits=(10, 2), default=0.0, required=True
    )

    @api.constrains("installment_amount")
    def _check_installment_constraints(self):
        for record in self:
            if record.installment_amount != record.advance_id.installment_value:
                raise ValidationError("Installment amount must be equal to the advance installment value.")


class FarmerFinancialAdvances(models.Model):
    _name = "farmers.financial.advances"
    _description = "Farmers Financial Advances"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    farmer_id = fields.Many2one("res.partner", string="Farmer Name", required=True)
    advance_amount = fields.Float(string="Advance Amount", help="The amount requested as an advance", digits=(10, 2), default=0.0, required=True)
    advance_start_date = fields.Date(string="Advance Start Date", required=True)
    num_installments = fields.Integer(
        string="Number of Installments", help="The number of months over which the advance will be repaid", required=True, default=1
    )
    installment_value = fields.Float(string="Installment Value (Week)", compute="_compute_installment_value", digits=(10, 2))
    deducation_period = fields.Integer(string="Deducation Period (Week)", required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id, required=True)
    advance_end_date = fields.Date(string="Advance End Date", compute="_compute_advance_end_date", default=False)
    # account_payment_id = fields.Many2one("account.payment", string="Account Payment", required=False)
    total_pay = fields.Char(string="Total Pay", required=False, compute="_compute_total_pay")
    stage = fields.Selection(
        [
            ("draft", "Draft"),
            ("post", "Post"),
        ],
        string="Stage",
        default="draft",
        required=True,
        tracking=1
    )
    installment_ids = fields.One2many(
        "farmers.financial.installments",
        "advance_id",
        string="Installments",
    )
    account_move_id = fields.Many2one("account.move", string="Account Move", required=False)

    @api.depends("advance_amount", "num_installments")
    def _compute_installment_value(self):
        for record in self:
            record.installment_value = record.advance_amount / record.num_installments

    @api.depends("advance_start_date", "num_installments", "deducation_period")
    def _compute_advance_end_date(self):
        for record in self:
            if record.advance_start_date:
                record.advance_end_date = record.advance_start_date + relativedelta(weeks=record.num_installments * record.deducation_period)
            else:
                record.advance_end_date = False

    @api.model
    def create(self, vals):
        record = super(FarmerFinancialAdvances, self).create(vals)
        return record

    def create_farmer_installments(self, i, record, entries_journal_id,account_debit_id, account_credit_id):
        sum_date = record.advance_start_date + relativedelta(weeks=i * record.deducation_period)
        new_record = self.create_account_move(record, account_debit_id,account_credit_id,record.installment_value,record.farmer_id.id,sum_date,entries_journal_id,record.currency_id.id)
        record.env["farmers.financial.installments"].create(
            {
                "advance_id": record.id,
                "description": "Installment Of " + str(sum_date),
                "installment_date": sum_date,
                "installment_amount": record.installment_value,
                "account_move_id": new_record.id,
            }
        )
        
    def create_account_move(self,record, account_debit_id,account_credit_id,installment_value,farmer_id,sum_date,entries_journal_id,currency_id):
        line_ids = [
            [
            0,
            "virtual_55",
                {
                    "partner_id": farmer_id, # record.farmer_id.id
                    "name": False,
                    "date_maturity": False,
                    "tax_ids": [],
                    "debit":installment_value , # record.installment_value
                    "credit": 0,
                    "account_id": account_debit_id,
                    "balance": installment_value , # record.installment_value
                    "discount_date": False,
                    "discount_amount_currency": 0,
                    "tax_tag_ids": [],
                    "display_type": "product",
                    "sequence": 100,
                }
            ],
            [
                0,
                "virtual_59",
                {
                    "partner_id": farmer_id, # record.farmer_id.id
                    "name": False,
                    "date_maturity": False,
                    "tax_ids": [],
                    "debit": 0,
                    "account_id": account_credit_id,
                    "credit": installment_value , # record.installment_value
                    "balance": -installment_value , # record.installment_value
                    "discount_date": False,
                    "discount_amount_currency": 0,
                    "tax_tag_ids": [],
                    "display_type": "product",
                    "sequence": 100,
                }
            ]
                    ]
        new_record = record.env["account.move"].create(
            {
                "date": sum_date,
                "auto_post": "no",
                "auto_post_until": False,
                "extract_state": "no_extract_requested",
                "extract_word_ids": [],
                "deferred_move_ids": [],
                "deferred_original_move_ids": [],
                "journal_id": entries_journal_id,
                "show_name_warning": False,
                "posted_before": False,
                "move_type": "entry",
                "payment_state": "not_paid",
                "currency_id": currency_id, # record.currency_id.id
                "statement_line_id": False,
                "origin_payment_id": False,
                "tax_cash_basis_created_move_ids": [],
                "show_update_fpos": False,
                "name": "/",
                "partner_id": False,
                "quick_edit_total_amount": 0,
                "ref": False,
                "invoice_vendor_bill_id": False,
                "invoice_date": False,
                "payment_reference": False,
                "partner_bank_id": False,
                "invoice_date_due": False,
                "invoice_payment_term_id": False,
                "delivery_date": False,
                "invoice_line_ids": [],
                "narration": False,
                'line_ids': line_ids,
            }
        )
        new_record._compute_name()
        return new_record

    def create_account_payment(self, record):
        # create new account.payment record then
        get_configuration = self.env["financial.configuration"].search([], limit=1)
        account_payment_vals = {
            "partner_id": record.farmer_id.id,
            "amount": record.advance_amount,
            "date": record.advance_start_date,
            "state": "draft",
            "payment_type": "outbound",
            "journal_id": get_configuration.journal_id.id if get_configuration.journal_id else False,
            "payment_method_id": get_configuration.payment_method_id.id if get_configuration.payment_method_id else False,
            "memo": get_configuration.memo_payment,
            "partner_bank_id": get_configuration.partner_bank_id.id if get_configuration.partner_bank_id else False,
        }
        new_accounting_payment = self.env["account.payment"].create(account_payment_vals)
        return new_accounting_payment

    def write(self, vals):
        res = super(FarmerFinancialAdvances, self).write(vals)
        update_installments = "advance_amount" in vals or "num_installments" in vals or "deducation_period" in vals
        update_payment = "farmer_id" in vals or "advance_amount" in vals or "advance_start_date" in vals or 'deducation_period' in vals
        config = self.env["financial.configuration"].search([], limit=1)
        entries_journal_id = config.entries_journal_id.id
        account_debit_id = config.account_debit_id.id
        account_credit_id = config.account_credit_id.id
        account_debit_farmer_id = config.account_depit_farmer_id.id
        account_credit_farmer_id = config.account_credit_farmer_id.id
        for record in self:
            if record.stage == "post":
                self.update_farmer_installments(update_installments, update_payment, record, entries_journal_id, account_debit_id, account_credit_id, account_debit_farmer_id, account_credit_farmer_id)
        return res

    def update_farmer_installments(self, update_installments, update_payment, record, entries_journal_id, account_debit_id, account_credit_id, account_debit_farmer_id, account_credit_farmer_id):

        # remove all installments and create new ones
        if update_installments:
            account_move_ids = record.env["farmers.financial.installments"].search([("advance_id", "=", record.id)]).mapped("account_move_id")
            # make account move ids archived
            if account_move_ids:
                account_move_ids.unlink()
            record.env["farmers.financial.installments"].search([("advance_id", "=", record.id)]).unlink()
            for i in range(record.num_installments):
                self.create_farmer_installments(i, record, entries_journal_id, account_debit_id, account_credit_id)
        if update_payment:
            if record.account_move_id:
                record.account_move_id.unlink()
            new_record = self.create_account_move(record, account_debit_farmer_id,account_credit_farmer_id,record.advance_amount,record.farmer_id.id,record.advance_end_date,entries_journal_id,record.currency_id.id)
            record.account_move_id = new_record.id
            # if record.account_payment_id:
            #     record.account_payment_id.write(
            #         {
            #             "partner_id": record.farmer_id.id,
            #             "amount": record.advance_amount,
            #             "date": record.advance_start_date,
            #         }
            #     )

    def post_farmer_financial(self):
        for record in self:
            if record.stage == "draft":
                # create account.payment record
                # if not record.account_payment_id:
                #     new_accounting_payment = self.create_account_payment(record)
                #     record.account_payment_id = new_accounting_payment.id
                # else:
                #     record.account_payment_id.write(
                #         {
                #             "partner_id": record.farmer_id.id,
                #             "amount": record.advance_amount,
                #             "date": record.advance_start_date,
                #         }
                #     )
                # # get all account.move.ids and delete them
                account_move_ids = record.env["farmers.financial.installments"].search([("advance_id", "=", record.id)]).mapped("account_move_id")
                if account_move_ids:
                    account_move_ids.unlink()
                config = self.env["financial.configuration"].search([], limit=1)
                entries_journal_id = config.entries_journal_id.id
                account_debit_id = config.account_debit_id.id
                account_credit_id = config.account_credit_id.id
                account_debit_farmer_id = config.account_depit_farmer_id.id
                account_credit_farmer_id = config.account_credit_farmer_id.id
                if not record.account_move_id :
                    new_record =self.create_account_move(record, account_debit_farmer_id,account_credit_farmer_id,record.advance_amount,record.farmer_id.id,record.advance_end_date,entries_journal_id,record.currency_id.id)
                    record.account_move_id = new_record.id
                for i in range(record.num_installments):
                    self.create_farmer_installments(i, record, entries_journal_id, account_debit_id, account_credit_id)
                record.stage = "post"

    @api.depends("advance_amount","installment_ids")
    def _compute_total_pay(self):
        for record in self:
            total_pay = 0
            for installment in record.installment_ids:
                if installment.account_move_state == "posted":
                    total_pay += installment.installment_amount
            total_pay=f"Pay : {total_pay} / {record.advance_amount}, Remaining : {record.advance_amount - total_pay}"
            record.total_pay = total_pay
            
    @api.model
    def get_total_unpaid_amount(self):
        
        print("get_total_unpaid_amount")
        # Query to get sum of all unpaid invoices
        return 1234.56
class FarmerFinancialInstallment(models.Model):
    _name = "farmers.financial.installments"
    _description = "Farmers Financial Installments"

    advance_id = fields.Many2one("farmers.financial.advances", string="Advance ID", required=True, ondelete="cascade")
    description = fields.Char(string="Description", help="Description of the installment", required=True)
    installment_date = fields.Date(string="Installment Date", required=True)
    account_move_id = fields.Many2one("account.move", string="Account Move", required=False)
    installment_amount = fields.Float(
        string="Installment Amount (Week)", help="The amount to be paid as an installment", digits=(10, 2), default=0.0, required=True
    )
    account_move_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
        ],
        string="Account Move State",
        related="account_move_id.state",
        store=True,
    )


class FinancialConfiguration(models.Model):
    _name = "financial.configuration"
    _description = "Financial Configuration"

    journal_id = fields.Many2one("account.journal", string="Payment Journal", required=True)# domain=[("type", "in", ["bank", "cash", "credit"])]
    payment_method_id = fields.Many2one("account.payment.method", string="Payment Method", required=True)
    partner_bank_id = fields.Many2one("res.partner.bank", string="Partner Bank", required=True)
    memo_payment = fields.Char(string="Memo Payment", required=False)
    entries_journal_id = fields.Many2one(
        "account.journal",
        string="Entries Journal",
    )
    account_debit_id = fields.Many2one("account.account", string="Account Debit", required=False)
    account_credit_id = fields.Many2one("account.account", string="Account Credit", required=False)
    account_depit_farmer_id = fields.Many2one("account.account", string="Account Debit Farmer", required=False)
    account_credit_farmer_id = fields.Many2one("account.account", string="Account Credit Farmer", required=False)
    
    @api.model
    def init(self):
        # Check if the record exists, if not create it
        if not self.search([]):
            # get first instance from all fields if exists
            # ['bank', 'cash', 'credit']
            journal = self.env["account.journal"].search([("type", "in", ["bank", "cash", "credit"])], limit=1)
            payment_method = self.env["account.payment.method"].search([], limit=1)
            entry_journal = self.env["account.journal"].search([], limit=1)
            partner_bank = self.env["res.partner.bank"].search([], limit=1)
            account_debit = self.env["account.account"].search([], limit=1)
            self.create(
                {
                    "journal_id": journal.id if journal else False,
                    "payment_method_id": payment_method.id if payment_method else False,
                    "partner_bank_id": partner_bank.id if partner_bank else False,
                    "entries_journal_id": entry_journal.id if entry_journal else False,
                    "memo_payment": "",
                    "account_debit_id": account_debit.id if account_debit else False,
                    "account_credit_id": account_debit.id if account_debit else False,
                    "account_depit_farmer_id": account_debit.id if account_debit else False,
                    "account_credit_farmer_id": account_debit.id if account_debit else False,
                }
            )

    @api.model
    def default_get(self, fields_list):
        # delete all records and create new one
        res = super(FinancialConfiguration, self).default_get(fields_list)
        existing_record = self.search([], limit=1)
        if existing_record:
            res.update(
                {
                    "journal_id": existing_record.journal_id.id,
                    "payment_method_id": existing_record.payment_method_id.id,
                    "partner_bank_id": existing_record.partner_bank_id.id,
                    "entries_journal_id": existing_record.entries_journal_id.id,
                    "memo_payment": existing_record.memo_payment,
                    "account_debit_id": existing_record.account_debit_id.id,
                    "account_credit_id": existing_record.account_credit_id.id,
                    "account_depit_farmer_id": existing_record.account_depit_farmer_id.id,
                    "account_credit_farmer_id": existing_record.account_credit_farmer_id.id,
                }
            )
        return res

    @api.model
    def create(self, vals):
        # Prevent creation of multiple records
        existing_record = self.search([], limit=1)
        if existing_record:
            existing_record.write(vals)
            return existing_record
        return super(FinancialConfiguration, self).create(vals)




class HrEmployeeInherit(models.Model):
    _inherit = "res.partner"

    financial_advance_ids = fields.One2many("employees.financial.advances", "employee_id", string="Financial Advances")

    show_financial_advances_tab = fields.Boolean(
        string="Show Financial Advances Tab",
        compute='_compute_show_financial_advances_tab',
        help="Determines if the Financial Advances tab should be visible."
    )
    def _compute_show_financial_advances_tab(self):
        for partner in self:
            # Show tab if the user is an HR manager or the employee is the same as the logged-in user
            partner.show_financial_advances_tab = not (
                self.env.user.has_group('hr.group_hr_manager') or
                partner.user_id == self.env.user
            )
class FinancialAdvanceEmployee(models.Model):
    _inherit = "hr.employee"
    financial_advance_ids = fields.One2many(
        'employees.financial.advances',  # Target model
        compute='_compute_financial_advance_ids',  # Compute method
        string='Financial Advances',
        store=False  # Optional: Set to True if you want to store the value in the database
    )
    show_financial_advances_tab = fields.Boolean(
        string="Show Financial Advances Tab",
        compute='_compute_show_financial_advances_tab',
        help="Determines if the Financial Advances tab should be visible."
    )
    @api.depends("work_contact_id.financial_advance_ids",'user_id.partner_id.financial_advance_ids')
    def _compute_financial_advance_ids(self):
        for record in self:
            related_partners = self._get_related_partners()
            if len(related_partners) == 1:
                record.financial_advance_ids = related_partners[0].financial_advance_ids
            else:
                data = []
                for partner in related_partners:
                    data.extend(partner.financial_advance_ids)
                record.financial_advance_ids = data


    @api.depends()
    def _compute_show_financial_advances_tab(self):
        for employee in self:
            # Show tab if the user is an HR manager or the employee is the same as the logged-in user
            employee.show_financial_advances_tab = not (
                self.env.user.has_group('hr.group_hr_manager') or
                employee.user_id == self.env.user
            )
            
