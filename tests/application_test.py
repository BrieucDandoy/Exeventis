from utils import Account
from utils import Dog

from exeventis.application import Application
from exeventis.recorder_store import RecorderStore
from exeventis.recorders.memory import EventMemoryRecorder

account_recorder = EventMemoryRecorder([Account], name="Account recorder")
dog_recorder = EventMemoryRecorder([Dog], name="dog recorder")
global_recorder = EventMemoryRecorder(name="global recorder")
recorder_store = RecorderStore(recorders=[account_recorder, dog_recorder, global_recorder])
service = Application(recorder_store=recorder_store)


def test_application():
    dog: Dog = Dog("medor")
    dog.add_trick("jump")
    dog.add_trick("sleep")
    dog.remove_trick("jump")
    service.save(dog)

    dog_id = dog._id
    dog_copy: Dog = service.get(originator_id=dog_id)

    assert dog._id == dog_copy._id
    assert dog.tricks == dog_copy.tricks
    assert dog.name == dog_copy.name


if __name__ == "__main__":
    test_application()
