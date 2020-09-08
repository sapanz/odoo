import astroid
from pylint import checkers, interfaces


class OdooBaseChecker(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker
    name = 'odoo'

    msgs = {
        'E8503': (
            'Raise inside unlink override.',
            'raise-unlink-override',
            'Raising errors is not allowed inside unlink overrides, '
            'you can create a method and decorate it with '
            '@api.ondelete(at_uninstall=False), only use '
            'at_uninstall=True if you know what you are doing.'
        )
    }

    @staticmethod
    def _will_raise(node):
        body = getattr(node, 'body', [])
        if any(isinstance(n, astroid.Raise) for n in body):
            return True
        for sub_node in body:
            res = OdooBaseChecker._will_raise(sub_node)
            if res:
                return res
        return False

    @checkers.utils.check_messages('raise-unlink-override')
    def visit_classdef(self, node):
        if not any(getattr(n, 'name', False) == 'BaseModel' for n in node.ancestors()):
            return
        for sub_node in node.body:
            if (isinstance(sub_node, astroid.FunctionDef)
            and sub_node.name == 'unlink'
            and self._will_raise(sub_node)):
                self.add_message('raise-unlink-override', node=sub_node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
