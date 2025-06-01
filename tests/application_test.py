from utils import Account
from utils import Dog

from exeventis.application import Application
from exeventis.recorders.memory import EventMemoryRecorder

account_recorder = EventMemoryRecorder([Account], name="Account recorder")
dog_recorder = EventMemoryRecorder([Dog], name="dog recorder")
global_recorder = EventMemoryRecorder(name="global recorder")
service = Application(recorders=[account_recorder, dog_recorder, global_recorder])


def test_application():
    dog: Dog = Dog("medor")
    dog.add_trick("jump")
    dog.add_trick("sleep")
    dog.remove_trick("jump")
    service.save(dog)

    dog_id = dog._id
    dog_copy: Dog = service.get(originator_id=dog_id)

    assert dog == dog_copy
