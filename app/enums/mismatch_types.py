from enum import Enum

class MismatchType(Enum):
    PENDING_STATUS = "Status is Pending"
    NO_SWIPE = "Swipe data missing"
    SHORT_SWIPE = "Swipe time less than 4 hours"
    SHORT_HALF_SWIPE = "Swipe time less than 2 hours"
    NO_WFH = "WFH not marked"
    NO_LEAVE = "Leave not marked"
    SHORT_LEAVE = "Leave marked less than 6 hours"
    SHORT_HALF_LEAVE = "Leave marked less than 3 hours"
    # Add other mismatch types as needed
