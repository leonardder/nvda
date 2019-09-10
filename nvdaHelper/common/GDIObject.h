/*
This file is a part of the NVDA project.
Copyright 2018-2019 NV Access Limited, Babbage B.V.
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License version 2.0, as published by
    the Free Software Foundation.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
This license can be found at:
http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
*/

#pragma once

#include <windows.h>

// A Smart GDI object handle.
class GDIObject {
	private:
	HGDIOBJ _hGDIObj  {nullptr};
	GDIObject(const GDIObject&)=delete;
	const GDIObject& operator=(const GDIObject&)=delete;

	public:

	GDIObject(HGDIOBJ h=nullptr): _hGDIObj(h) {};

	void destroy() {
		if(_hGDIObj) {
			DeleteObject(_hGDIObj);
			_hGDIObj=nullptr;
		}
	}

	GDIObject& operator=(HGDIOBJ h) {
		destroy();
		_hGDIObj=h;
		return *this;
	}

	operator HGDIOBJ() {
		return _hGDIObj;
	}

	operator HRGN() {
		return static_cast<HRGN>(_hGDIObj);
	}

	operator bool() {
		return static_cast<bool>(_hGDIObj);
	}

	~GDIObject() {
		destroy();
	}

};
