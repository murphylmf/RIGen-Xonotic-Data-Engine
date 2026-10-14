#include "modalcontroller.qh"

#include "button.qh"

	.vector ModalController_initialSize;
	.vector ModalController_initialOrigin;
	.vector ModalController_initialFontScale;
	.float ModalController_initialAlpha;
	.vector ModalController_buttonSize;
	.vector ModalController_buttonOrigin;
	.float ModalController_state;
	.float ModalController_factor;
	.entity ModalController_controllingButton;

	void ModalController_initializeDialog(entity me, entity root)
	{
		me.hideAll(me, 1);
		me.showChild(me, root, '0 0 0', '0 0 0', 1);                                 
	}

	void TabButton_Click(entity button, entity tab)
	{
		if (tab.ModalController_state == 1) return;
		tab.parent.hideAll(tab.parent, 0);
		button.forcePressed = 1;
		tab.ModalController_controllingButton = button;
		tab.parent.showChild(tab.parent, tab, button.origin, button.size, 0);
	}

	void DialogOpenButton_Click(entity button, entity tab)
	{
		DialogOpenButton_Click_withCoords(button, tab, button.origin, button.size);
	}

	void DialogOpenButton_Click_withCoords(entity button, entity tab, vector theOrigin, vector theSize)
	{
		if (tab.ModalController_state) return;
		if (button) button.forcePressed = 1;
		if (tab.parent.focusedChild) tab.parent.focusedChild.saveFocus(tab.parent.focusedChild);
		tab.ModalController_controllingButton = button;
		tab.parent.showChild(tab.parent, tab, theOrigin, theSize, 0);
	}

	void DialogCloseButton_Click(entity button, entity tab)
	{
		tab.parent.hideChild(tab.parent, tab, 0);
	}

	void ModalController_resizeNotify(entity me, vector relOrigin, vector relSize, vector absOrigin, vector absSize)
	{
		me.resizeNotifyLie(me, relOrigin, relSize, absOrigin, absSize, ModalController_initialOrigin, ModalController_initialSize, ModalController_initialFontScale);
	}

	void ModalController_switchState(entity me, entity other, float state, float skipAnimation)
	{
		float previousState;
		previousState = other.ModalController_state;
		if (state == previousState && !skipAnimation) return;
		other.ModalController_state = state;
		switch (state)
		{
			case 0:
				other.ModalController_factor = 1 - other.Container_alpha / other.ModalController_initialAlpha;
				             
				break;
			case 1:
				other.ModalController_factor = other.Container_alpha / other.ModalController_initialAlpha;
				if (previousState == 0 && !skipAnimation)
				{
					other.Container_origin = other.ModalController_buttonOrigin;
					other.Container_size = other.ModalController_buttonSize;
				}
				             
				break;
			case 2:
				other.ModalController_factor = bound(0, (1 - other.Container_alpha / other.ModalController_initialAlpha) / me.fadedAlpha, 1);
				                     
				break;
		}
		if (skipAnimation) other.ModalController_factor = 1;
	}

	void ModalController_draw(entity me)
	{
		entity e;
		entity front;
		float animating;
		float f;                     
		float df;                       
		float prevFactor, targetFactor;
		vector targetOrigin, targetSize;
		float targetAlpha;
		vector fs;
		animating = 0;

		front = NULL;
		for (e = me.firstChild; e; e = e.nextSibling)
			if (e.ModalController_state)
			{
				if (front) me.switchState(me, front, 2, 0);
				front = e;
			}
		if (front) me.switchState(me, front, 1, 0);

		df = frametime * 3;                    

		for (e = me.firstChild; e; e = e.nextSibling)
		{
			if (e.ModalController_state == 2)
			{
				                       
				targetOrigin = e.Container_origin;              
				targetSize = e.Container_size;                  
				targetAlpha = me.fadedAlpha * e.ModalController_initialAlpha;
			}
			else if (e.ModalController_state == 1)
			{
				             
				targetOrigin = e.ModalController_initialOrigin;
				targetSize = e.ModalController_initialSize;
				targetAlpha = e.ModalController_initialAlpha;
			}
			else
			{
				             
				targetOrigin = e.Container_origin;              
				targetSize = e.Container_size;                  
				targetAlpha = 0;
			}

			f = (e.ModalController_factor = min(1, e.ModalController_factor + df));
			if (f == 1)
			{
				prevFactor = 0;
				targetFactor = 1;
				e.Container_origin = targetOrigin;
				e.Container_size = targetSize;
				me.setAlphaOf(me, e, targetAlpha);
			}
			else
			{
				prevFactor = (1 - f) / (1 - f + df);
				if (!e.ModalController_state)                                             
				{
					me.setAlphaOf(me, e, e.Container_alpha  * prevFactor);
				}
				else
				{
					animating = 1;
					targetFactor = df / (1 - f + df);

					if (e.ModalController_state == 1)
					{
						e.Container_origin = e.Container_origin * prevFactor + targetOrigin * targetFactor;
						e.Container_size   = e.Container_size   * prevFactor + targetSize   * targetFactor;
					}
					me.setAlphaOf(me, e, e.Container_alpha  * prevFactor + targetAlpha  * targetFactor);
				}
			}
			                                              
			                                     
			      
			                                        
			                                                           
			               
			                                                        

			if (e.ModalController_state == 1)
			{
				fs = globalToBoxSize(e.Container_size, e.ModalController_initialSize);
				e.Container_fontscale_x = fs.x * e.ModalController_initialFontScale.x;
				e.Container_fontscale_y = fs.y * e.ModalController_initialFontScale.y;
			}
		}

		if (animating || !me.focused) me.setFocus(me, NULL);
		else me.setFocus(me, front);
		SUPER(ModalController).draw(me);
	}

	void ModalController_addTab(entity me, entity other, entity tabButton)
	{
		me.addItem(me, other, '0 0 0', '1 1 1', 1);
		tabButton.onClick = TabButton_Click;
		tabButton.onClickEntity = other;
		other.tabSelectingButton = tabButton;
		if (other == me.firstChild)
		{
			tabButton.forcePressed = 1;
			other.ModalController_controllingButton = tabButton;
			me.showChild(me, other, '0 0 0', '0 0 0', 1);
		}
	}

	void ModalController_addItem(entity me, entity other, vector theOrigin, vector theSize, float theAlpha)
	{
		SUPER(ModalController).addItem(me, other, theOrigin, theSize, (other == me.firstChild) ? theAlpha : 0);
		other.ModalController_initialFontScale = other.Container_fontscale;
		other.ModalController_initialSize = other.Container_size;
		other.ModalController_initialOrigin = other.Container_origin;
		other.ModalController_initialAlpha = theAlpha;                                       
		if (other.ModalController_initialFontScale == '0 0 0') other.ModalController_initialFontScale = '1 1 0';
	}

	void ModalController_showChild(entity me, entity other, vector theOrigin, vector theSize, float skipAnimation)
	{
		if (other.ModalController_state == 0 || skipAnimation)
		{
			me.setFocus(me, NULL);
			if (!skipAnimation)
			{
				other.ModalController_buttonOrigin = globalToBox(theOrigin, me.origin, me.size);
				other.ModalController_buttonSize = globalToBoxSize(theSize, me.size);
			}
			me.switchState(me, other, 1, skipAnimation);
		}                                           
	}

	void ModalController_hideAll(entity me, float skipAnimation)
	{
		entity e;
		for (e = me.firstChild; e; e = e.nextSibling)
			me.hideChild(me, e, skipAnimation);
	}

	void ModalController_hideChild(entity me, entity other, float skipAnimation)
	{
		if (other.ModalController_state || skipAnimation)
		{
			me.setFocus(me, NULL);
			me.switchState(me, other, 0, skipAnimation);
			if (other.ModalController_controllingButton)
			{
				other.ModalController_controllingButton.forcePressed = 0;
				other.ModalController_controllingButton = NULL;
			}
		}                                                               
	}
