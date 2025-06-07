from utils import Account

from exeventis.application import Application
from exeventis.recorder_store import RecorderStore
from exeventis.recorders.sqlalchemy import SqlRecorder
from exeventis.transcoders import StandartTranscoderStore

sql_recorder = SqlRecorder(
    database_url="sqlite:///:memory:",
    name="SQL recorder",
    transcoder_store=StandartTranscoderStore(),
)
recorder_store = RecorderStore(recorders=[sql_recorder])
service = Application(recorder_store=recorder_store)


def test_application_get():
    account: Account = Account("test")
    account.add(10)
    account.subtract(1)
    service.save(account)

    account_copy = service.get(account._id)

    assert account_copy._id == account._id
    assert account.balance == account.balance


if __name__ == "__main__":
    test_application_get()
