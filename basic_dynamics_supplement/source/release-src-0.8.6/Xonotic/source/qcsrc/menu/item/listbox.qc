#include "listbox.qh"

	bool ListBox_isScrolling(entity me)
	{
		return me.scrollPos != me.scrollPosTarget;
	}

	void ListBox_scrollToItem(entity me, int i)
	{
		                                                                            
		                                 
		if (me.itemHeight == 1)                                               
		{
			me.needScrollToItem = i;
			return;
		}

		i = bound(0, i, me.nItems - 1);

		                                                            
		                                              
		if (i < me.getFirstFullyVisibleItemAtScrollPos(me, me.scrollPos))
		{
			                     
			me.scrollPosTarget = me.getItemStart(me, i);
		}
		else if (i > me.getLastFullyVisibleItemAtScrollPos(me, me.scrollPos))
		{
			                     
			if (i == me.nItems - 1) me.scrollPosTarget = me.getTotalHeight(me) - 1;
			else me.scrollPosTarget = me.getItemStart(me, i + 1) - 1;
		}
	}

	void ListBox_setSelected(entity me, float i)
	{
		i = bound(0, i, me.nItems - 1);
		me.scrollToItem(me, i);
		me.selectedItem = i;
	}
	void ListBox_resizeNotify(entity me, vector relOrigin, vector relSize, vector absOrigin, vector absSize)
	{
		SUPER(ListBox).resizeNotify(me, relOrigin, relSize, absOrigin, absSize);
		me.controlWidth = me.scrollbarWidth / absSize.x;
	}
	void ListBox_configureListBox(entity me, float theScrollbarWidth, float theItemHeight)
	{
		me.scrollbarWidth = theScrollbarWidth;
		me.itemHeight = theItemHeight;
	}

	float ListBox_getTotalHeight(entity me)
	{
		return me.nItems * me.itemHeight;
	}
	float ListBox_getItemAtPos(entity me, float pos)
	{
		return floor(pos / me.itemHeight);
	}
	float ListBox_getItemStart(entity me, float i)
	{
		return me.itemHeight * i;
	}
	float ListBox_getItemHeight(entity me, float i)
	{
		return me.itemHeight;
	}

	float ListBox_getLastFullyVisibleItemAtScrollPos(entity me, float pos)
	{
		return me.getItemAtPos(me, pos + 0.999) - 1;
	}
	float ListBox_getFirstFullyVisibleItemAtScrollPos(entity me, float pos)
	{
		return me.getItemAtPos(me, pos + 0.001) + 1;
	}
	float ListBox_keyDown(entity me, float key, float ascii, float shift)
	{
		if (key == K_MWHEELUP)
		{
			me.scrollPosTarget = max(me.scrollPosTarget - 0.5, 0);
		}
		else if (key == K_MWHEELDOWN)
		{
			me.scrollPosTarget = min(me.scrollPosTarget + 0.5, max(0, me.getTotalHeight(me) - 1));
		}
		else if (key == K_PGUP || key == K_KP_PGUP)
		{
			if (me.selectionDoesntMatter)
			{
				me.scrollPosTarget = max(me.scrollPosTarget - 0.5, 0);
				return 1;
			}

			float i = me.selectedItem;
			float a = me.getItemHeight(me, i);
			for ( ; ; )
			{
				--i;
				if (i < 0) break;
				a += me.getItemHeight(me, i);
				if (a >= 1) break;
			}
			me.setSelected(me, i + 1);
		}
		else if (key == K_PGDN || key == K_KP_PGDN)
		{
			if (me.selectionDoesntMatter)
			{
				me.scrollPosTarget = min(me.scrollPosTarget + 0.5, me.nItems * me.itemHeight - 1);
				return 1;
			}

			float i = me.selectedItem;
			float a = me.getItemHeight(me, i);
			for ( ; ; )
			{
				++i;
				if (i >= me.nItems) break;
				a += me.getItemHeight(me, i);
				if (a >= 1) break;
			}
			me.setSelected(me, i - 1);
		}
		else if (key == K_UPARROW || key == K_KP_UPARROW)
		{
			if (me.selectionDoesntMatter)
			{
				me.scrollPosTarget = max(me.scrollPosTarget - me.itemHeight, 0);
				return 1;
			}

			me.setSelected(me, me.selectedItem - 1);
		}
		else if (key == K_DOWNARROW || key == K_KP_DOWNARROW)
		{
			if (me.selectionDoesntMatter)
			{
				me.scrollPosTarget = min(me.scrollPosTarget + me.itemHeight, me.nItems * me.itemHeight - 1);
				return 1;
			}

			me.setSelected(me, me.selectedItem + 1);
		}
		else if (key == K_HOME || key == K_KP_HOME)
		{
			me.setSelected(me, 0);
		}
		else if (key == K_END || key == K_KP_END)
		{
			me.setSelected(me, me.nItems - 1);
		}
		else
		{
			return 0;
		}
		return 1;
	}
	float ListBox_mouseMove(entity me, vector pos)
	{
		me.mouseMoveOffset = -1;
		if (pos_x < 0) return 0;
		if (pos_y < 0) return 0;
		if (pos_x >= 1) return 0;
		if (pos_y >= 1) return 0;
		if (pos_x < 1 - me.controlWidth)
		{
			me.mouseMoveOffset = pos.y;
		}
		else
		{
			me.setFocusedItem(me, -1);
			me.mouseMoveOffset = -1;
		}
		return 1;
	}
	float ListBox_mouseDrag(entity me, vector pos)
	{
		float hit;
		me.updateControlTopBottom(me);
		me.dragScrollPos = pos;
		if (me.pressed == 1)
		{
			hit = 1;
			if (pos.x < 1 - me.controlWidth - me.tolerance.x * me.controlWidth) hit = 0;
			if (pos.y < 0 - me.tolerance.y) hit = 0;
			if (pos.x >= 1 + me.tolerance.x * me.controlWidth) hit = 0;
			if (pos.y >= 1 + me.tolerance.y) hit = 0;
			if (hit)
			{
				                         
				float d;
				d = (pos.y - me.pressOffset) / (1 - (me.controlBottom - me.controlTop)) * (me.getTotalHeight(me) - 1);
				me.scrollPosTarget = me.previousValue + d;
			}
			else
			{
				me.scrollPosTarget = me.previousValue;
			}
			me.scrollPosTarget = min(me.scrollPosTarget, me.getTotalHeight(me) - 1);
			me.scrollPosTarget = max(me.scrollPosTarget, 0);
		}
		else if (me.pressed == 2)
		{
			int clickeditem = me.getItemAtPos(me, me.scrollPos + pos.y);
			me.setSelected(me, clickeditem);
			me.setFocusedItem(me, clickeditem);
			me.mouseMoveOffset = -1;
		}
		return 1;
	}
	METHOD(ListBox, mousePress, bool(ListBox this, vector pos))
	{
		if (pos.x < 0) return false;
		if (pos.y < 0) return false;
		if (pos.x >= 1) return false;
		if (pos.y >= 1) return false;
		this.dragScrollPos = pos;
		this.updateControlTopBottom(this);
		if (pos.x >= 1 - this.controlWidth)
		{
			                                                         
			if (pos.y < this.controlTop)
			{
				          
				this.scrollPosTarget = max(this.scrollPosTarget - 1, 0);
			}
			else if (pos.y > this.controlBottom)
			{
				            
				this.scrollPosTarget = min(this.scrollPosTarget + 1, this.getTotalHeight(this) - 1);
			}
			else
			{
				this.pressed = 1;
				this.pressOffset = pos.y;
				this.previousValue = this.scrollPos;
			}
		}
		else
		{
			                                                                                                                                
			this.pressed = 2;
			                                           
			int clickeditem = this.getItemAtPos(this, this.scrollPos + pos.y);
			this.setSelected(this, clickeditem);
			this.setFocusedItem(this, clickeditem);
		}
		return true;
	}
	void ListBox_setFocusedItem(entity me, int item)
	{
		float focusedItem_save = me.focusedItem;
		me.focusedItem = (item < me.nItems) ? item : -1;
		if (focusedItem_save != me.focusedItem)
		{
			me.focusedItemChangeNotify(me);
			if (me.focusedItem >= 0) me.focusedItemAlpha = SKINALPHA_LISTBOX_FOCUSED;
		}
	}
	float ListBox_mouseRelease(entity me, vector pos)
	{
		if (me.pressed == 1)
		{
			                       
			                                             
		}
		else if (me.pressed == 2)
		{
			me.pressed = 3;                                                                      
			                     
			                                      
			int clickeditem = me.getItemAtPos(me, me.scrollPos + pos.y);
			me.setSelected(me, clickeditem);
			me.setFocusedItem(me, clickeditem);
			                                 
			if (me.nItems > 0)
			{
				vector where = globalToBox(pos, eY * (me.getItemStart(me, me.selectedItem) - me.scrollPos), eX * (1 - me.controlWidth) + eY * me.getItemHeight(me, me.selectedItem));

				if ((me.selectedItem == me.lastClickedItem && clickeditem == me.selectedItem) && (time < me.lastClickedTime + 0.3))
					me.doubleClickListBoxItem(me, me.selectedItem, where);
				else
					me.clickListBoxItem(me, me.selectedItem, where);

				me.lastClickedItem = me.selectedItem;
				me.lastClickedTime = time;
			}
		}
		me.pressed = 0;
		return 1;
	}
	void ListBox_focusLeave(entity me)
	{
		                                                    
		                                          
		                                              
		me.pressed = 0;
		me.setFocusedItem(me, -1);
		me.mouseMoveOffset = -1;
	}
	void ListBox_updateControlTopBottom(entity me)
	{
		float f;
		                                                                              
		if (me.getTotalHeight(me) <= 1)
		{
			                                                                        
			me.controlTop = 0;
			me.controlBottom = 1;
			me.scrollPos = 0;
		}
		else
		{
			                                             
			me.scrollPos = min(me.scrollPos, me.getTotalHeight(me) - 1);
			                                                   
			me.scrollPos = max(me.scrollPos, 0);
			                                                                                     
			me.controlTop = max(0, me.scrollPos / me.getTotalHeight(me));
			me.controlBottom = min((me.scrollPos + 1) / me.getTotalHeight(me), 1);

			float minfactor;
			minfactor = 2 * me.controlWidth / me.size.y * me.size.x;
			f = me.controlBottom - me.controlTop;
			if (f < minfactor)                        
			{
				                                
				                              
				                              
				                                
				f = (minfactor - 1) / (f - 1);
				me.controlTop = me.controlTop * f + 0 * (1 - f);
				me.controlBottom = me.controlBottom * f + 1 * (1 - f);
			}
		}
	}
	AUTOCVAR(menu_scroll_averaging_time, float, 0.16, "smooth scroll averaging time");
	                                             
	AUTOCVAR(menu_scroll_averaging_time_pressed, float, 0.06, "smooth scroll averaging time when dragging the scrollbar");
	void ListBox_draw(entity me)
	{
		vector fillSize = '0 0 0';

		                                                                                 
		if (me.mouseMoveOffset != -1) me.setFocusedItem(me, me.getItemAtPos(me, me.scrollPos + me.mouseMoveOffset));

		if (me.needScrollToItem >= 0)
		{
			me.scrollToItem(me, me.needScrollToItem);
			me.needScrollToItem = -1;
		}
		if (me.scrollPos != me.scrollPosTarget)
		{
			float averaging_time = (me.pressed == 1)
				? autocvar_menu_scroll_averaging_time_pressed
				: autocvar_menu_scroll_averaging_time;
			                                             
			float f = averaging_time ? exp(-frametime / averaging_time) : 0;
			me.scrollPos = me.scrollPos * f + me.scrollPosTarget * (1 - f);
			if (fabs(me.scrollPos - me.scrollPosTarget) < 0.001) me.scrollPos = me.scrollPosTarget;
		}

		if (me.pressed == 2) me.mouseDrag(me, me.dragScrollPos);                             
		me.updateControlTopBottom(me);
		fillSize.x = (1 - me.controlWidth);
		if (me.alphaBG) draw_Fill('0 0 0', '0 1 0' + fillSize, me.colorBG, me.alphaBG);
		if (me.controlWidth)
		{
			draw_VertButtonPicture(eX * (1 - me.controlWidth), strcat(me.src, "_s"), eX * me.controlWidth + eY, me.color2, 1);
			if (me.getTotalHeight(me) > 1)
			{
				vector o, s;
				o = eX * (1 - me.controlWidth) + eY * me.controlTop;
				s = eX * me.controlWidth + eY * (me.controlBottom - me.controlTop);
				if (me.pressed == 1) draw_VertButtonPicture(o, strcat(me.src, "_c"), s, me.colorC, 1);
				else if (me.focused) draw_VertButtonPicture(o, strcat(me.src, "_f"), s, me.colorF, 1);
				else draw_VertButtonPicture(o, strcat(me.src, "_n"), s, me.color, 1);
			}
		}
		draw_SetClip();
		vector oldshift = draw_shift;
		vector oldscale = draw_scale;

		int i = me.getItemAtPos(me, me.scrollPos);
		float y = me.getItemStart(me, i) - me.scrollPos;
		for ( ; i < me.nItems && y < 1; ++i)
		{
			draw_shift = boxToGlobal(eY * y, oldshift, oldscale);
			vector relSize = eX * (1 - me.controlWidth) + eY * me.getItemHeight(me, i);
			vector absSize = boxToGlobalSize(relSize, me.size);
			draw_scale = boxToGlobalSize(relSize, oldscale);
			me.drawListBoxItem(me, i, absSize, (me.selectedItem == i), (me.focusedItem == i));
			y += relSize.y;
		}
		draw_ClearClip();

		draw_shift = oldshift;
		draw_scale = oldscale;
		SUPER(ListBox).draw(me);
	}

	void ListBox_focusedItemChangeNotify(entity me)
	{}

	void ListBox_clickListBoxItem(entity me, float i, vector where)
	{
		                  
	}

	void ListBox_doubleClickListBoxItem(entity me, float i, vector where)
	{
		                  
	}

	void ListBox_drawListBoxItem(entity me, int i, vector absSize, bool isSelected, bool isFocused)
	{
		draw_Text('0 0 0', sprintf(_("Item %d"), i), eX * (8 / absSize.x) + eY * (8 / absSize.y), (isSelected ? '0 1 0' : '1 1 1'), 1, 0);
	}
