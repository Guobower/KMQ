from odoo import fields,models,api

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_get_suggested_recipients(self):
        """ Returns suggested recipients for ids. Those are a list of
        tuple (partner_id, partner_name, reason), to be managed by Chatter. """

	#This method overrided.
        result = dict((res_id, []) for res_id in self.ids)
        if 'partner_id' in self._fields:
            for obj in self.sudo():  # SUPERUSER because of a read on res.users that would crash otherwise
                if not obj.partner_id:
                    continue
                obj._message_add_suggested_recipient(result, partner=obj.partner_id, reason=self._fields['partner_id'].string)
        return result

