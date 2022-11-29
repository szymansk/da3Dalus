import tigl3.configuration as TConfig

RIGHT_MAIN_WING_INDEX = 1


class Configuration:
    """
        This class is responsible for extracting the CPACS component from the tigl handle
    """

    def __init__(self, tigl_handle):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)

    def get_wing(self, wing_index):
        return self.cpacs_configuration.get_wing(wing_index)

    def get_right_main_wing(self):
        return self.cpacs_configuration.get_wing(RIGHT_MAIN_WING_INDEX)

    def get_fuselage(self, fuselage_index=1):
        """
        :param fuselage_index: the id of the fuselage by default set to 1 (main fuselage)
        :return:
        """
        return self.cpacs_configuration.get_fuselage(fuselage_index)

    def get_cpacs_configuration(self):
        return self.cpacs_configuration
