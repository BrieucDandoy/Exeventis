from utils import Account

from exeventis.application import Application
from exeventis.recorders.sqlalchemy import SqlRecorder
from exeventis.transcoders import StandartTranscoderStore

sql_recorder = SqlRecorder(
    database_url="sqlite:///:memory:",
    name="SQL recorder",
    transcoder_store=StandartTranscoderStore(),
)
service = Application(recorders=[sql_recorder])


def test_application_get():
    account: Account = Account("test")
    account.add(10)
    account.subtract(1)
    service.save(account)

    account_copy = service.get(account._id)

    print(account.__dict__)
    print(account_copy.__dict__)
    assert account_copy == account
