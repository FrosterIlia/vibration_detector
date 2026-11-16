class ResonanceMapper:
    def __init__(self, config):
        self.printer = config.get_printer()
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('MAP_HELLO', self.cmd_MAP_HELLO,
                               desc="Check resonance_mapper is loaded")

    def cmd_MAP_HELLO(self, gcmd):
        gcmd.respond_info("resonance_mapper alive")

def load_config(config):
    return ResonanceMapper(config)