def classFactory(iface):
    from .plugin import EcwConverterPlugin
    return EcwConverterPlugin(iface)
