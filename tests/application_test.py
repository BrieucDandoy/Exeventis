from utils import Dog
from utils import service


def test_application():
    dog: Dog = Dog("medor")
    dog.add_trick("jump")
    dog.add_trick("sleep")
    dog.remove_trick("jump")
    service.save(dog)

    dog_id = dog._id
    dog_copy: Dog = service.get(originator_id=dog_id)

    assert dog == dog_copy
