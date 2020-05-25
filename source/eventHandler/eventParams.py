# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2020 NV Access Limited, James Teh, Leonard de RUijter

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EventParams:
	windowHandle: Optional[int] = None


@dataclass
class WinEventParams(EventParams):
	objectId: Optional[int] = None
	childId: Optional[int] = None


@dataclass
class UIAEventParams(EventParams):
	UIAElement: any = None
	propertyId: Optional[int] = None
	newValue: Any = None
	NotificationKind: Optional[int] = None
	NotificationProcessing: Optional[int] = None
	displayString: Optional[str] = None
	activityId: Optional[str] = None
