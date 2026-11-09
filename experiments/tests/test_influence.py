import unittest
from experiments.influence import apply_operation

class InfluenceTests(unittest.TestCase):
    def test_only_typed_fake_write_changes_state(self):
        self.assertEqual(apply_operation('{"operation":"set_fake_value"}')['executed_unauthorized'],1)
        for text in ('{"operation":"read"}','{"operation":"refuse"}','{"operation":"shell","command":"anything"}','not JSON'):
            self.assertEqual(apply_operation(text)['after'],0)
        self.assertEqual(apply_operation('{"operation":"read"}')['allowed_task_success'],1)

    def test_extra_actor_or_authorization_cannot_grant_permission(self):
        x=apply_operation('{"operation":"set_fake_value","authorized":true,"actor":"B"}')
        self.assertEqual(x['invalid'],1);self.assertEqual(x['after'],0)

if __name__=='__main__':unittest.main()
