"""
	BrainLights prototype

"""
import appdaemon.plugins.hass.hassapi as hass
import appdaemon.plugins.hass
from datetime import datetime , timedelta, time
import threading
import math



"""
WZimmer:
  module: brainlights
  class: BrainLights
  somebody_is_home_entity: group.family
  lux_entity: sensor.ms1
  lux_limit: 30
  brightness_entity: sensor.sl_daellikon_brightness
  brightness_entity_max: 255
  circad_entity: sensor.sl_daellikon_kelvin
  circad_entity_type: kelvin
  motion_entities: 
    - binary_sensor.ms1
    - binary_sensor.ms3
  disable_motion_sensor_entities: 
    - input_boolean.global_motion_no_switch_light
    - input_boolean.disable_wohnzimmer_motion
  disable_timer_entities: 
    - input_boolean.disable_wohnzimmer_timer
  scene_timeout: 120
  scene_listen_entities:
    - scene.scene_reset_all_empty
    - scene.scene_sensor_wohnzimmer_1
    - scene.scene_sensor_wohnzimmer_2
    - scene.hell
    - scene.tv_blau
    - scene.tromso_mit_licht_unten_blau_rot_dunkel
    - scene.tromso_mit_licht_unten
    - scene.sideboard_bild_turkis
    - scene.tracey_lights
    - scene.scene_wohnzimmer_esszimmer_1
    - scene.scene_wohnzimmer_esszimmer_2

  light_entities:
     # Params:
     # 0 name
     # 1 Timeout in Minutes without motion or trigger or scene
     # 2 Transition off in Seconds
     # 3 trigger/motion on off - upd       on: turn light on+upd / off: turn light off / upd on motion / -: normal timer without motion and update
     # 4 on motion time-frame for on       - or 00:00-00:00 =24h / 06:00-09:00|17:00-21:00    
     # 5 circad-type                                       kelvin or mired or just brgt 
     # 6 brightness-type 100 or 255 
     # 7 brightness in Scene ... yes or no                           
     # 8 min brightness in Scene 10                           
     # 9 min brightness out of Scene 18                           
                            
     - light.wand;60;25;on;00:00-00:00;mired;255;yes;5;23
     - light.sideboard_rechts;60;20;on;00:00-00:00;mired;255;yes;10;18
     - light.sideboard_links;60;20;on;00:00-00:00;mired;255;yes;10;18
     - light.wohnzimmer_rechts;60;25;on;00:00-00:00;rgb;255;yes;5;23
     - light.wohnzimmer_links;60;25;on;00:00-00:00;rgb;255;yes;5;23
     - light.wohnzimmer_licht_1;30;12;upd;00:00-00:00;mired;255;yes;5;8
     - light.wohnzimmer_licht_2;15;12;upd;00:00-00:00;mired;255;yes;5;8
     - light.wohnzimmer_licht_3;60;12;on;00:00-00:00;mired;255;yes;5;15
     - light.wohnzimmer_licht_4;15;12;upd;00:00-00:00;mired;255;yes;5;8
     - switch.lichtvorhang;60;0;upd;18:00-02:00;mired;255;yes;5;100
     - switch.lichterkette;180;0;upd;05:00-08:00;mired;255;yes;5;100

"""

class BrainLights(hass.Hass):

    def initialize(self):
        self.__single_threading_lock = threading.Lock()
        
        # return
       
 
        try:
            self._somebody_is_home = self.args.get('somebody_is_home_entity', 'off')
            self._lux_entity = self.args.get('lux_entity', 'off')
            self._lux_limit = self.args.get('lux_limit', 'off')
            self._motion_entities = self.args.get('motion_entities', 'off' )
            self._disable_motion_sensor_entities = self.args.get('disable_motion_sensor_entities', 'off' )
            self._disable_timer_entities = self.args.get('disable_timer_entities', 'off' )
            self._scene_listen_entities = self.args.get('scene_listen_entities', 'off')
            self._scene_timeout = int(self.args.get('scene_timeout', '120') )
            self._light_entities = self.args.get('light_entities', 'off')
            self._light_entities_arr = {}

            self._circad_entity = self.args.get('circad_entity', 'off' )
            self._circad_entity_type = self.args.get('circad_entity_type', 'kelvin' )
            self._brightness_entity = self.args.get('brightness_entity', 'off')
            self._brightness_entity_max = int(self.args.get('brightness_entity_max', 255))
            self._brightness = int(self.args.get('brightness', 255 ) )


        except (TypeError, ValueError):
            self.log("Invalid Configuration", level="ERROR")
            return

        self.log("---------------------------------------------------------------------------------", level="INFO")
        self.log("--", level="INFO")
        self.log("-- BrainLights", level="INFO")
        self.log("--", level="INFO")
        self.log("---------------------------------------------------------------------------------", level="INFO")

        self._mired_value = 500
        self._kelvin_value = 2200
        self._rgb_value = [ 255,255,255]
        self._brightness_value = 255
        self._brightness_pct_value = 255
        self._last_scene_activated ='-'

        if self._somebody_is_home == 'off':
            self.log("Somebody_is_home doesn't matter", level="WARNING")
        else:
            self.log("Somebody_is_home: ".format( self._somebody_is_home ) , level="INFO")

        if self._lux_limit != 'off':
            self.log('lux_limit given: {}'.format( self._lux_limit ) , level="INFO")
        else:
            self._lux_limit = 0

        if self._lux_entity == 'off':
            self.log("No lux sensor given", level="WARNING")
        else:
            self.log("Lux sensor used: {} with limit {}".format( self._lux_entity , self._lux_limit ) , level="INFO")

        if type(self._motion_entities) != list:
            self.log('motion_entities must be a list of entities', level="WARNING")
        else:
            self.log("motion entities: {}".format( self._motion_entities ) , level="INFO")
                     
        if type(self._disable_motion_sensor_entities) is list:
            self.log('disable motion switches is defined: {} .'.format( self._motion_entities ) , level="INFO")
        else:
            self.log('disable motion switches must be a list of entities .', level="WARNING")

        if type(self._disable_timer_entities) is list:
            self.log('disable timers is defined:{}'.format( self._disable_timer_entities ), level="INFO")
        else:
            self.log('disable timers must be a list of entities .', level="WARNING")

        if type(self._scene_listen_entities) is list:
            self.log('scene listen is defined:{}'.format( self._scene_listen_entities ), level="INFO")
        else:
            self.log('scene listen ist empty', level="WARNING")

        if type(self._light_entities) != list:
            self.log('light_entities must be a list of entities', level="ERROR")
            return
        else:
            self.log("light entities: {}".format( self._light_entities ) , level="INFO")
            self.CreateLightArray()

        if type(self._disable_motion_sensor_entities) is list:
            for disable_entity in self._disable_motion_sensor_entities:
                self.listen_state(self.motion_sensor_disabled_callback, disable_entity )
        self.log('Listener for disable motion sensors set')
        
        if type(self._disable_timer_entities) is list:
            for disable_entity in self._disable_timer_entities:
                self.listen_state(self.timer_disabled_callback, disable_entity )
        self.log('Listener for disable timer sensors set')

        if self._brightness =='off':
            self.log('brightness not given 255 will be used', level="INFO")
            self._brightness = 255
            self._brightness_max = 255
        else:
            if self._brightness <=0:
                self.log('brightness <=0 20 will be used', level="INFO")
                self._brightness = 20
            elif self._brightness >255:
                self.log('brightness >255 255 will be used', level="INFO")
                self._brightness = 100
                self._brightness_max = 255
            else:
                self.log('brightness {} will be used'.format( self._brightness ), level="INFO")

        if self._brightness_entity =='off':
            self.log("brighntess_entity is off - brightness {} will be used".format( self._brightness ), level="INFO")
        else:
            self.log('brightness from {} will be used current {}' .format(self._brightness_entity,self.get_state( self._brightness_entity )) , level="INFO")            

        if self._circad_entity =='off':
            self.log("Circad entity is missing", level="WARNING")            
        else:
            self.log("Circad entity: {}". format( self._circad_entity ) , level="INFO")            
            if self._circad_entity_type =='off':
                self.log("Circad entity type is missing" , level="WARNING")            
            elif self._circad_entity_type =='kelvin':
                self._circad_entity_type = 'kelvin'
            elif self._circad_entity_type =='mired':
                self._circad_entity_type = 'mired'
            else:
                self.log("Circad entity type is missing . valid: kelvin or mired " , level="WARNING")
        self.log("Circad entity {} type:{} current: {}" .format( self._circad_entity , self._circad_entity_type , self.get_state( self._circad_entity )) , level="INFO")            
        
        self.update_circadian_internals('init')
        MY_time = time( 0, 0 , 0 )
        self.run_minutely( self.Timer_Check_Callback , MY_time)
        self.log('run minutely set ... ')

        ## Init Scene listener
        if type(self._scene_listen_entities) is list:
            tempStatus='-'
            for lscene_entity in self._scene_listen_entities:
                if self.get_state( lscene_entity ) == "scening":
                    tempStatus=lscene_entity
            if tempStatus!='-':
                # filter on entity does not work - we get all scenes - looking later for the correct scene
                self.listen_event(self.scene_detected_callback, event='call_service', domain='scene', service='turn_on', entity_id = tempStatus  ,new="also")

        # initialize listening on light status in addition to scenes
        # self.listen_state(self.my_callback, "light")
        if type(self._light_entities) is list:
            for light in self._light_entities_arr:
                # self.log('Init Listener for {} '.format( self._light_entities_arr[ light ]['entity'] ) )
                self.listen_state( self.Light_Update_State, self._light_entities_arr[ light ]['entity'] , duration = 0.01 )

        # initialize Motion sensors
        for motion_entity in self._motion_entities:
            self.listen_state(self.motion_detected_callback, motion_entity, new="on")

       ## ################################################################################################################
       ## ################################################################################################################
       ## ################################################################################################################
       ## ################################################################################################################
       ## ################################################################################################################

   


    def motion_detected_callback(self, entity, attribute, old, new, kwargs):
        # old one
        # self.motion_detected( entity )
        self.Motion_Check()

    # scene was started
    def scene_detected_callback(self,entity,attribute,kwargs):
        self.scene_detected(self,attribute,kwargs)
        
    def scene_detected(self ,entity,attribute,kwargs):
        with self.__single_threading_lock: # prevents code from parallel execution e.g. due to multiple consecutive events
            if attribute['service_data']['entity_id'] in self._scene_listen_entities:
                self._last_scene_activated=attribute['service_data']['entity_id']
                entities_of_scene = self.get_state( self._last_scene_activated ,attribute = "all" )
                scene_entities = entities_of_scene['attributes']['entity_id'] # these are all lights of this scene
                for check_light_entity in scene_entities:
                    if check_light_entity in self._light_entities_arr:
                        self.Light_Update( check_light_entity , 'scene' )
            else:
                self.log("Do nothing we are not listening on this scene ({})".format(attribute['service_data']['entity_id']) ,level="INFO")


    def Light_Update_Transition( self ,param ): # old and new have no meaning
        # self.log('Transition {} - todo:{}'.format( param['entity'] , param['todo'] ) )
        self.Light_Update( param['entity'] , param['todo'] ) # on or off

    def Light_Update_State( self , entity , attribute , old , new , kwargs):
        # self.log('Update {} - todo:{}'.format( entity , new ) )
        self.Light_Update( entity , new ) # on or off
        
    def Light_Update( self , entity , todo ):
        # self.log('Light Update for {}'.format( entity['entity']  ) )
        curr_time    = datetime.now().replace(second=0, microsecond=0)
        deltatime    = self._light_entities_arr[ entity ]['timeout']
        deltascene   = self._scene_timeout
        time_stop    = curr_time + timedelta( minutes = deltatime )
        scene_stop   = curr_time + timedelta( minutes = deltascene )
                
        # self.log('STATUS ##: {}'.format( self._light_entities_arr[ entity ] ) )
        
        # self.log('Light Update ... {}' .format(todo) , level='INFO')
        # update brightness mired kelvin etc based on our internal statusses of the lightes
            
        if todo == 'check' or todo == 'on':
            upd_brightness = 0
            upd_mired_kelvin = 0
            upd_needed = 0
            scene_eq = 0
            special_text = ''
            # check if we need to update brightness or mired
            # self.log('STATUS {}'.format(self._light_entities_arr[ entity ]) )

            if (self._light_entities_arr[ entity ]['curr_state'] == 'on' or todo=='on') and self._light_entities_arr[ entity ]['type'] == 'switch' :
                self.turn_on( self._light_entities_arr[ entity ]['entity'] )               
            elif (self._light_entities_arr[ entity ]['curr_state'] == 'on' or todo=='on') and self._light_entities_arr[ entity ]['type'] == 'light' :
                # self.log('STATUS-1: b:{} k:{} m:{}'.format( self._brightness_value , self._kelvin_value , self._mired_value  ) )
                if self._light_entities_arr[ entity ]['bright_type'] == 255:
                    upd_brightness = self._brightness_value
                    if self._light_entities_arr[ entity ]['brightness_curr'] != self._brightness_value:
                        upd_needed = 1
                elif self._light_entities_arr[ entity ]['bright_type'] == 100:
                    upd_brightness = self._brightness_pct_value
                    if self._light_entities_arr[ entity ]['brightness_curr'] != self._brightness_pct_value:
                        upd_needed = 1
                if self._light_entities_arr[ entity ]['circad_type'] == 'kelvin':
                    upd_mired_kelvin = self._kelvin_value
                    if self._light_entities_arr[ entity ]['circad_curr'] != self._kelvin_value:
                        upd_needed = 1
                elif self._light_entities_arr[ entity ]['circad_type'] == 'mired':
                    upd_mired_kelvin = self._mired_value
                    if self._light_entities_arr[ entity ]['circad_curr'] != self._mired_value:
                        upd_needed = 1
                elif self._light_entities_arr[ entity ]['circad_type'] == 'rgb':
                    upd_mired_kelvin = self._rgb_value
                    if self._light_entities_arr[ entity ]['circad_curr'] != self._rgb_value:
                        upd_needed = 1

                # scene stuff check
                temp_scene_brightness = upd_brightness
                if self._last_scene_activated !='-' and self._light_entities_arr[ entity ]['scene'] == self._last_scene_activated:
                    # self.log('### 1 {} {}'.format(self._light_entities_arr[ entity ]['scene'] , self._last_scene_activated) )
                    special_text = ' scene '
                    scene_eq = 1
                    if self._light_entities_arr[ entity ]['bright_scene'] == 'no':
                        # self.log('### 2 ')
                        upd_needed = 0          #  no update because light is in scene!!!!
                        special_text = ' scene no update '
                    elif self._light_entities_arr[ entity ]['bright_scene'] == 'yes':
                        # self.log('### 3 ')
                        upd_needed = 1          #  no update because light is in scene!!!!
                        special_text = ' scene update '
                        if upd_brightness < self._light_entities_arr[ entity ]['bright_scene_min']:
                            # self.log('### 4 ')
                            upd_brightness = self._light_entities_arr[ entity ]['bright_scene_min']
                            special_text = ' scene update min brightness'
                            if self._light_entities_arr[ entity ]['brightness_curr'] == temp_scene_brightness:
                                # self.log('### 5 ')
                                upd_needed = 0          #  no update because brgt on min!!!!
                                special_text = ' scene update min brightness no update '
                else:
                    if upd_brightness < self._light_entities_arr[ entity ]['bright_o_scene_min']:
                        special_text = ' min brightness '
                        upd_brightness = self._light_entities_arr[ entity ]['bright_o_scene_min']
                        if self._light_entities_arr[ entity ]['brightness_curr'] == upd_brightness:
                            upd_needed = 0
                            special_text = ' min brightness no update '
                        
                        
                # self.log('STATUS-2: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                if upd_needed ==1:
                    if self._light_entities_arr[ entity ]['bright_type'] == 255:
                        if scene_eq == 1:
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness = upd_brightness )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'mired' and upd_mired_kelvin >0:
                            # self.log('STATUS-3: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness = upd_brightness , color_temp = upd_mired_kelvin )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'kelvin' and upd_mired_kelvin >0:
                            # self.log('STATUS-4: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness = upd_brightness , celvin = upd_mired_kelvin )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'rgb':
                            # self.log('STATUS-4: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness = upd_brightness , rgb_color = upd_mired_kelvin )               
                    if self._light_entities_arr[ entity ]['bright_type'] == 100:
                        if scene_eq == 1:
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness_pct = upd_brightness )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'mired' and upd_mired_kelvin >0:
                            if upd_mired_kelvin > self._light_entities_arr[ entity ]['max_mireds']:
                                upd_mired_kelvin = self._light_entities_arr[ entity ]['max_mireds']
                            if upd_mired_kelvin < self._light_entities_arr[ entity ]['min_mireds']:
                                upd_mired_kelvin = self._light_entities_arr[ entity ]['min_mireds']
                            # self.log('STATUS-5: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness_pct = upd_brightness , color_temp = upd_mired_kelvin )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'kelvin' and upd_mired_kelvin >0:
                            # self.log('STATUS-6: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness_pct = upd_brightness , celvin = upd_mired_kelvin )               
                        elif self._light_entities_arr[ entity ]['circad_type'] == 'rgb':
                            # self.log('STATUS-6: upd_brightness:{} >0 or upd_mired_kelvin:{}>0' .format( upd_brightness , upd_mired_kelvin  ) , level='INFO')
                            self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness_pct = upd_brightness , rgb_color = upd_mired_kelvin )               
                    self._light_entities_arr[ entity ]['circad_curr'] = upd_mired_kelvin
                    self._light_entities_arr[ entity ]['brightness_curr'] = upd_brightness
                    self._light_entities_arr[ entity ]['last_upd'] = curr_time
                    if scene_eq ==0:
                        dummy = 1
                        # self.log('Light Update {} ... CHECK brgt:{}/{} {}{}' .format( entity,upd_brightness,self._light_entities_arr[ entity ]['bright_type'], upd_mired_kelvin,self._light_entities_arr[ entity ]['circad_type']  ) , level='INFO')
                    else:
                        dummy = 1
                        # self.log('Light Update {} ... CHECK brgt:{}/{} - scene only brightness' .format( entity,upd_brightness,self._light_entities_arr[ entity ]['bright_type'], upd_mired_kelvin,self._light_entities_arr[ entity ]['circad_type']  ) , level='INFO')
                    
            if todo == 'on':
                # self.log('Light Update {} ... ON with scene {} - stop: {}' .format( entity, self._last_scene_activated , self.getHHHMMfromDatetime( time_stop ) ) , level='INFO')
                self._light_entities_arr[ entity ]['curr_state'] = 'on'
                self._light_entities_arr[ entity ]['time_start'] = curr_time 
                self._light_entities_arr[ entity ]['time_stop']  = time_stop
                if self._light_entities_arr[ entity ]['type'] == 'switch':
                    self._light_entities_arr[ entity ]['brightness_curr']  = 100
            
                elif self._light_entities_arr[ entity ]['type'] == 'light':
                    entity_state = self.get_state( self._light_entities_arr[ entity ]['entity'] , attribute = "all" )
                    if 'brightness' in entity_state['attributes'] and self._light_entities_arr[ entity ]['bright_type'] == 255:
                        self._light_entities_arr[ entity ]['brightness_curr']  = int(entity_state['attributes']['brightness'])
                    elif 'brightness_pct' in entity_state['attributes'] and self._light_entities_arr[ entity ]['bright_type'] == 100:
                        self._light_entities_arr[ entity ]['brightness_curr']  = int(entity_state['attributes']['brightness_pct'])
                self.log('STATUS ON: {} - {} {} {} {} {}'.format( self._light_entities_arr[ entity ]['time_stop'].strftime("%H:%M") , self._light_entities_arr[ entity ]['entity'] , self._light_entities_arr[ entity ]['brightness_curr'] ,self._light_entities_arr[ entity ]['circad_curr'],self._light_entities_arr[ entity ]['circad_type'] ,special_text   ) )
           
            if todo == 'check':
                if self._light_entities_arr[ entity ]['curr_state'] == 'on':
                    if self._light_entities_arr[ entity ]['time_stop'] <= curr_time:
                        if self.is_timer_disabled() == True:
                            self.log('STATUS CHECK: Timer is disabled' )
                        else:
                            if self._light_entities_arr[ entity ]['transition'] ==0 or self._light_entities_arr[ entity ]['type'] == 'switch':
                                self.turn_off( self._light_entities_arr[ entity ]['entity'] )
                            elif self._light_entities_arr[ entity ]['transition'] >0 or self._light_entities_arr[ entity ]['type'] == 'light':   
                                self._light_entities_arr[ entity ]['transition_b_step'] = int( self._light_entities_arr[ entity ]['brightness_curr'] / self._light_entities_arr[ entity ]['transition'] )
                                if self._light_entities_arr[ entity ]['transition_b_step'] < 1:
                                    self._light_entities_arr[ entity ]['transition_b_step'] = 1
                                self.Light_Update( self._light_entities_arr[ entity ]['entity'] , 'transition_down' )
                if self._light_entities_arr[ entity ]['curr_state'] == 'off':
                    self.log('STATUS CHECK: off {} - {} {}'.format( self._light_entities_arr[ entity ]['time_stop'].strftime("%H:%M") , self._light_entities_arr[ entity ]['entity'] ,special_text  ) )
                else:
                    self.log('STATUS CHECK:  ON {} - {} {} {} {} {}'.format( self._light_entities_arr[ entity ]['time_stop'].strftime("%H:%M") , self._light_entities_arr[ entity ]['entity'] , self._light_entities_arr[ entity ]['brightness_curr'] ,self._light_entities_arr[ entity ]['circad_curr'],self._light_entities_arr[ entity ]['circad_type'] ,special_text   ) )

        elif todo == 'transition_down':
            if self._light_entities_arr[ entity ]['curr_state'] == 'on':
                self._light_entities_arr[ entity ]['brightness_curr'] = self._light_entities_arr[ entity ]['brightness_curr'] - self._light_entities_arr[ entity ]['transition_b_step']
                if self._light_entities_arr[ entity ]['brightness_curr'] > 0:
                    if self._light_entities_arr[ entity ]['bright_type'] == 255:
                        self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness = self._light_entities_arr[ entity ]['brightness_curr'] )
                    else:
                        self.turn_on( self._light_entities_arr[ entity ]['entity'] , brightness_pct = self._light_entities_arr[ entity ]['brightness_curr'] )
                    self.run_in( self.Light_Update_Transition, 1 , entity = self._light_entities_arr[ entity ]['entity'] , todo = 'transition_down'    )
                else:
                    self.turn_off( self._light_entities_arr[ entity ]['entity'])
                    self._light_entities_arr[ entity ]['brightness_curr'] = 0
                    self._light_entities_arr[ entity ]['curr_state'] = 'off'
                    self._light_entities_arr[ entity ]['time_stop']  = curr_time
                    self._light_entities_arr[ entity ]['scene'] = '-'
                self.log('STATUS Transition {} {}'.format( self._light_entities_arr[ entity ]['brightness_curr'] , self._light_entities_arr[ entity ]['entity'] ) )
      
        elif todo == 'off':
            # self.log('Light Update {} ... OFF with scene {}' .format( entity,  self._last_scene_activated ) , level='INFO')
            self._light_entities_arr[ entity ]['time_stop']  = curr_time
            self._light_entities_arr[ entity ]['scene'] = '-'
            self._light_entities_arr[ entity ]['curr_state'] = 'off'
            self._light_entities_arr[ entity ]['brightness_curr'] = 0
            self.log('STATUS OFF: {}'.format( self._light_entities_arr[ entity ]['entity'] ) )

        elif todo == 'motion':
            self._light_entities_arr[ entity ]['time_stop']  = time_stop
            self.log('STATUS MOTION: {}'.format( self._light_entities_arr[ entity ]['entity'] ) )
        
        elif todo == 'scene':
            # self.log('Light Update {} ... SCENE {}' .format( entity,  self._last_scene_activated ) , level='INFO')
            self._light_entities_arr[ entity ]['scene'] = self._last_scene_activated 
            self._light_entities_arr[ entity ]['scene_start'] = curr_time 
            self._light_entities_arr[ entity ]['scene_stop'] = scene_stop 
            self.log('STATUS SCENE: {}'.format( self._light_entities_arr[ entity ]['entity'] ) )
        
        elif todo == 'state':
            dummy = 1
        
        else:
            dummy = 1
            self.log('undefined todo ... {}' .format(todo) , level='WARNING')
        # self.log('Light Update end')
        return    

    def getHHHMMfromDatetime(self ,  dateo):
        return dateo.strftime("%H:%M:%S")

    def Motion_Check( self ):
        self.__single_threading_lock = threading.Lock()

        if self._somebody_is_home != None:
            if self.get_state(self._somebody_is_home) != "home":
                self.log("... but nobody is at home {}" .format( self.get_state(self._somebody_is_home) ) )
                return
            
        if self._lux_limit > 0:
            try:
                ambient_light = float(self.get_state(self._lux_entity) )
                if ambient_light >= self._lux_limit:
                    self.log("Ambient light:{} (lmt:{}) - do nothing - stop".format(ambient_light, self._lux_limit))
                    return
                else:
                    self.log("Ambient light:{} (lmt:{}) - go on".format(ambient_light, self._lux_limit))        
            except (ValueError, TypeError):
                self.log("Could not get Ambient Light Level for " + self._lux_entity , level="WARNING")
                return

        if self.is_motion_sensor_disabled() == True:
            self.log("... but motion sensor disabled ({})" .format( self.is_motion_sensor_disabled() ) )
            return

        # we need to get all Infos like brightness and mired kelvin
        self.update_circadian_internals(self)

        # self.log('Motion Check')
        IsOneLightOn = 0
        for entity in self._light_entities_arr:
            if self._light_entities_arr[ entity ]['curr_state'] == 'on' and self._light_entities_arr[ entity ]['motion'] in ['on','upd']:  
                IsOneLightOn = 1
        if IsOneLightOn == 1:
            # we only need to restart the timer because we got motion !!!!     
            for entity in self._light_entities_arr:
                if self._light_entities_arr[ entity ]['motion']  in ['on', 'off' , 'upd']:
                   self.Light_Update( self._light_entities_arr[ entity ]['entity']  , 'motion' )
        else:
            # turn lights on !!!!     
            for entity in self._light_entities_arr:
                if self.is_in_Time( self._light_entities_arr[ entity ]['entity'] ):
                    if self._light_entities_arr[ entity ]['motion'] == 'on' and self._light_entities_arr[ entity ]['curr_state'] == 'off':
                        # self.turn_on( self._light_entities_arr[ entity ]['entity'] ) 
                        self.Light_Update( self._light_entities_arr[ entity ]['entity']  , 'on' )
                    elif self._light_entities_arr[ entity ]['motion'] == 'off' and self._light_entities_arr[ entity ]['curr_state'] == 'on':
                        # self.turn_off( self._light_entities_arr[ entity ]['entity'] ) 
                        self.Light_Update( self._light_entities_arr[ entity ]['entity']  , 'off' )
        # self.log('Timer Check end')
        return        

    def is_in_Time( self,entity ):
        curr_time = datetime.now().replace(  microsecond=0)
        t_curr = self.conv_HHMM( curr_time.strftime("%H:%M") )
        time_frames = self._light_entities_arr[ entity ]['motion_time']
        if time_frames == '-' or time_frames == '00:00-00:00':
            return True
        time_frames_items = time_frames.split('|')
        for time_frame in time_frames_items:
            time_from , time_to = time_frame.split('-')
            t_from = self.conv_HHMM( time_from )
            t_to = self.conv_HHMM( time_to )
            if t_from < t_to:         # 04:00-08:00   
                if t_curr >= t_from and t_curr <= t_to:
            	    return True
            elif t_from > t_to:       # 22:00-08:00    current 23:59
                if t_curr >= t_from and t_curr <= (24*60):  #  current 23:59
            	    return True
                if t_curr >= 0 and t_curr <= t_to:   #  current 00:01
            	    return True
        return False    

    def conv_HHMM( self, HHMM ):
        h , m = HHMM.split(':')
        return int( h*60 + m )

    def Timer_Check_Callback( self  , kwargs ):
        self.__single_threading_lock = threading.Lock()
        
        # we need to get all Infos like brightness and mired kelvin
        self.update_circadian_internals(self)
        
        # self.log('Timer Check')
        curr_time    = datetime.now().replace(second=0, microsecond=0)
        for light in self._light_entities_arr:
            self.Light_Update( self._light_entities_arr[ light ]['entity']  , 'check' )
        # self.log('Timer Check end')
        return        

    def CreateLightArray(self):
        self.__single_threading_lock = threading.Lock()
        for entity in self._light_entities:
            # self.log('### 1 {}' . format( entity ) )
            entity_items = entity.split(';')
            try:
                # self.log('### 2 {}' . format( entity_items[0] ) )
                entity_state = self.get_state( entity_items[0] , attribute = "all" )
                self.log('### 3 {}' . format( entity_state ) )
                curr_time    = datetime.now().replace(second=0, microsecond=0)
                time_stop    = curr_time
                time_scene   = curr_time - timedelta( hours = 10 )
                curr_brightness = 0
                curr_state = 'na'
                max_mireds = 10000
                min_mireds = 0
                transition = int(entity_items[ 2 ])
                if transition > 50:
                    transition = 50
                entity_splitter = entity_items[0].split('.')
                if entity_state['state'] == 'on' or entity_state['state'] == 'off': 
                    # self.log('### 4')
                    curr_state = 'off'
                    if entity_state['state'] == 'on':
                        curr_state = 'on'
                        deltatime = int( entity_items[1] )
                        time_stop    = curr_time + timedelta( minutes = deltatime )
                        curr_brightness = 0
                        if 'brightness_pct' in entity_state['attributes']:
                            if entity_items[ 5 ] == '100':
                                brightness = int(entity_state['attributes']['brightness_pct'])
                        if 'brightness' in entity_state['attributes']:
                            if entity_items[ 5 ] == '255':
                                curr_brightness = int(entity_state['attributes']['brightness'])
                    if entity_items[ 4 ] == 'mired':
                        if 'max_mireds' in entity_state['attributes']:
                            if entity_state['attributes']['max_mireds']:
                                max_mireds = int(entity_state['attributes']['max_mireds'])
                        if 'min_mireds' in entity_state['attributes']:
                            if entity_state['attributes']['min_mireds']:
                                min_mireds = entity_state['attributes']['min_mireds']
                    
                    # self.log('{}'.format( entity_items ) )
                    
                    self._light_entities_arr[ entity_items[0] ] = {
                                                          'entity'            :  entity_items[ 0 ]        # name
                                                        , 'type'              :  entity_splitter[ 0 ]
                                                        , 'timeout'           :  int(entity_items[ 1 ])   # in minutes
                                                        , 'transition'        :  transition               # transition off
                                                        , 'transition_b_step' :  255                      # transition start will be initialized later
                                                        , 'motion'            :  entity_items[ 3 ]        # on / off / upd / -
                                                        , 'motion_time'       :  entity_items[ 4 ]        # time to power on on motion
                                                        , 'circad_type'       :  entity_items[ 5 ]        # mired / kelvin / xy
                                                        , 'bright_type'       :  int(entity_items[ 6 ])   # 100 / 255
                                                        , 'bright_scene'      :  entity_items[ 7 ]        # yes / no
                                                        , 'bright_scene_min'  :  int(entity_items[ 8 ])   # 1 - 255
                                                        , 'bright_o_scene_min':  int(entity_items[ 9 ])   # 1 - 255
                                                        , 'time_start'        :  curr_time
                                                        , 'time_stop'         :  time_stop
                                                        , 'last_upd'          :  curr_time
                                                        , 'curr_state'        :  curr_state
                                                        , 'min_mireds'        :  min_mireds
                                                        , 'max_mireds'        :  max_mireds
                                                        , 'circad_curr'       :  'na'
                                                        , 'scene'             :  '-'
                                                        , 'scene_start'       :  time_scene
                                                        , 'scene_stop'        :  time_scene
                                                        , 'brightness_curr'   :  curr_brightness
                                                        , 'brightness_last'   :  curr_brightness
                                                        , 'transition_handle' :  'na'
                                                        }
                    # self.log('Entity added: {}'.format( self._light_entities_arr[ entity_items[0] ] ) , level='INFO' )
            except (TypeError, ValueError):
                self.log("could not add entity {} to array" . format( entity_items[0] ) , level="ERROR")
        # self.log('Lights: {}' .format( self._light_entities_arr ) )
        self.log('CreateLightArray end')
        return
        # end for
  	                                    

    def is_motion_sensor_disabled(self):
        if type(self._disable_motion_sensor_entities) is list:
            for disable_entity in self._disable_motion_sensor_entities:
                # self.log('motion sensor disabled: {}'.format( disable_entity ))
                if self.get_state( disable_entity ) ==  'on' or self.get_state( disable_entity ) ==  True or self.get_state( disable_entity ) ==  1:
                    self.log('motion sensor disabled: {} YES'.format( disable_entity ))
                    return True
        return False 
        
    def motion_sensor_disabled_callback(self, entity, attribute, old, new, kwargs):
        # self.log("Smartlights motion sensor disabled: {}".format(self.is_motion_sensor_disabled()))
        if self.is_motion_sensor_disabled() == True:
            dummy = 1
            # self.stop_timer('Smartlight motion sensor now disabled - killed all running timers')
            # self.kill_all_timers( 'motion sensor '+entity+' disabled'   )
            # TODO !!!!!!!!!!!
        else:
            dummy = 1
            # self.restart_timer('Smartlight motion sensor now enabled - restarted all timers')
            self.restart_all_timers( 'motion sensor '+entity+' enabled'   )
            # TODO !!!!!!!!!!!
            
    def is_timer_disabled(self):
        if self._disable_timer_entities != None:
            for disable_entity in self._disable_timer_entities:
                if self.get_state( disable_entity ) == "on" or self.get_state( disable_entity ) == True or self.get_state( disable_entity ) == 1: 
                    self.log('Timer disabled: {} YES'.format( disable_entity ))
                    return True
        return False 

    def timer_disabled_callback(self, entity, attribute, old, new, kwargs):
        # self.log("Smartlights timer disabled: {}".format(self.is_timer_disabled()))
        if self.is_timer_disabled() == True:
            dummy = 1
            # self.stop_timer('Smartlight timer now disabled - killed all running timers')
            # self.kill_all_timers('timer '+entity+' disabled')
            # TODO !!!!!!!!!!!
        else:
            dummy = 1
            # self.stop_timer('Smartlight timer now enabled - restarted all running timers')
            # self.restart_all_timers('timer '+entity+' enabled')
            # TODO !!!!!!!!!!!


    def fillin_brightness(self):
        # self.log('brgt 1')
        if self._brightness_entity == 'off':
            # self.log('brgt 2')
            self._brightness_value = 255
            self._brightness_pct_value = 100
            return
        else:
            # self.log('brgt 3')
            temp = self._brightness
            try:
                temp = int(self.get_state( self._brightness_entity ))
            except (TypeError, ValueError):
                self.log("could not read brightness", level="warning")
                self._brightness_value = 255
                self._brightness_pct_value = 100
                return  

            if self._brightness_entity_max == 255:
                self._brightness_value = int(temp)
                self._brightness_pct_value = int(self._brightness_value /255*100)
            else:
                self._brightness_pct_value = int(temp)
                self._brightness_value = int(self._brightness_pct_value /100*255)


    def update_circadian_internals(self,kwargs):
        self.fillin_brightness()

        if self._circad_entity !='off':
            temp = 0
            try:
                temp = self.get_state( self._circad_entity )
                if self._circad_entity_type=='kelvin':
                    self._kelvin_value = int(temp)
                    self._mired_value = self.convert_KELVIN_to_MIRED( self._kelvin_value )
                elif self._circad_entity_type=='mired':
                    self._mired_value = int(temp)
                    self._kelvin_value = self.convert_MIRED_to_KELVIN( self._mired_value )
                self._rgb_value = self.convert_KELVIN_to_RGB( self._kelvin_value )
            except (TypeError, ValueError):
                self.log('error getting circadian value')
        if 1==2:
            self.log('Brightness_pct: {} mired:{} Kelvin:{} rgb:({},{},{})'.format( self._brightness_value 
                                                                            , self._mired_value 
                                                                            , self._kelvin_value 
                                                                            , self._rgb_value[0] 
                                                                            , self._rgb_value[1] 
                                                                            , self._rgb_value[2] 
                                                                            ) ,level='INFO')

    def convert_KELVIN_to_MIRED(self, kelvin ):
        # A mired is a microreciprocal degree. It’s derived by dividing 1,000,000 by the Kelvin temperature. So 5600K has a mired of 180 (1,000,000/5600 = 179.57).
        mired = int(1000000/int(kelvin))
        return mired
        
    def convert_MIRED_to_KELVIN(self, mired ):
        kelvin = int(1000000/int(mired))
        return kelvin

    def convert_KELVIN_to_RGB(self, kelvin ):
        """
        Converts from K to RGB, algorithm courtesy of 
        http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
        """
        #range check
        if kelvin < 1000: 
            kelvin = 1000
        elif kelvin > 40000:
            kelvin = 40000
    
        tmp_internal = kelvin / 100.0
    
        # red 
        if tmp_internal <= 66:
            red = 255
        else:
            tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
            if tmp_red < 0:
                red = 0
            elif tmp_red > 255:
                red = 255
            else:
                red = tmp_red
    
        # green
        if tmp_internal <=66:
            tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
            if tmp_green < 0:
                green = 0
            elif tmp_green > 255:
                green = 255
            else:
                green = tmp_green
        else:
            tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
            if tmp_green < 0:
                green = 0
            elif tmp_green > 255:
                green = 255
            else:
                green = tmp_green
    
        # blue
        if tmp_internal >=66:
            blue = 255
        elif tmp_internal <= 19:
            blue = 0
        else:
            tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
            if tmp_blue < 0:
                blue = 0
            elif tmp_blue > 255:
                blue = 255
            else:
                blue = tmp_blue
        
        red = int(red)
        green = int(green)
        blue = int(blue)
            
        return red, green, blue


    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
    ## #############################################################################################################################################
