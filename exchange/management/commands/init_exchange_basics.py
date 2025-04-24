from django.core.management.base import BaseCommand

from exchange.models import Exchange, Symbol, ExchangeSymbolShip, Asset


class Command(BaseCommand):
    help = 'Initializes basic exchange data like exchanges, assets, symbols, and relationships.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting basic exchange data initialization...'))

        # --- Exchanges ---
        # Define the exchanges you want to ensure exist
        exchanges_to_ensure = [
            {'name': 'binance', 'status': 'Active'},
            {'name': 'okx', 'status': 'Active'},
            {'name': 'huobi', 'status': 'Active'},
            {'name': 'bitmex', 'status': 'Active'},
            {'name': 'bybit', 'status': 'Active'},
            {'name': 'bitget', 'status': 'Active'},
        ]
        self.stdout.write("--- Seeding Exchanges ---")
        for ex_data in exchanges_to_ensure:
            exchange, created = Exchange.objects.get_or_create(
                name=ex_data['name'],
                defaults={'status': ex_data['status']}
            )
            if created:
                self.stdout.write(f"  Created Exchange: {exchange.name}")
            else:
                self.stdout.write(f"  Exchange exists: {exchange.name}")

        # --- Symbols to Ensure (used for both Asset and Symbol seeding) ---
        symbols_to_ensure = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']  # Add other symbols as needed

        # --- Assets --- derived from symbols_to_ensure
        self.stdout.write("\\n--- Seeding Assets ---")

        # Define the mapping for specific asset units
        ASSET_UNITS_MAP = {
            'USDT': 6,
            'BTC': 8,
            'ETH': 18,
            'SOL': 6,
        }
        DEFAULT_UNIT = 6  # Default unit for assets not in the map

        unique_asset_names = set()
        for sym_name in symbols_to_ensure:
            parts = sym_name.split('/')
            if len(parts) == 2:
                unique_asset_names.add(parts[0])  # Base asset
                unique_asset_names.add(parts[1])  # Quote asset
            else:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: Invalid symbol format '{sym_name}'. Skipping asset extraction."))

        for asset_name in unique_asset_names:
            # Determine unit using the map or default
            unit_value = ASSET_UNITS_MAP.get(asset_name, DEFAULT_UNIT)
            if unit_value == DEFAULT_UNIT and asset_name not in ASSET_UNITS_MAP:
                self.stdout.write(self.style.NOTICE(
                    f"  Asset '{asset_name}' not found in ASSET_UNITS_MAP. Using default unit: {unit_value}"))

            # Define defaults, including the determined unit and stablecoin status
            defaults = {'unit': unit_value}
            if asset_name in ['USDT', 'USDC', 'BUSD', 'DAI']:  # Add other known stablecoins
                defaults['is_stable'] = 'Yes'
            else:
                defaults['is_stable'] = 'No'

            asset, created = Asset.objects.get_or_create(
                name=asset_name,
                defaults=defaults
            )
            if created:
                self.stdout.write(f"  Created Asset: {asset_name}")
            else:
                self.stdout.write(f"  Asset exists: {asset_name}")

        # --- Symbols --- using previously defined symbols_to_ensure
        self.stdout.write("\\n--- Seeding Symbols ---")
        for sym_name in symbols_to_ensure:
            parts = sym_name.split('/')
            if len(parts) != 2:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: Invalid symbol format '{sym_name}'. Skipping symbol creation."))
                continue

            base_name, quote_name = parts[0], parts[1]

            try:
                base_asset = Asset.objects.get(name=base_name)
                quote_asset = Asset.objects.get(name=quote_name)
            except Asset.DoesNotExist as e:
                self.stdout.write(self.style.ERROR(
                    f"  Error: Required asset for symbol '{sym_name}' not found ({e}). Skipping symbol creation."))
                continue

            symbol, created = Symbol.objects.get_or_create(
                name=sym_name,
                defaults={
                    'base_asset': base_asset,
                    'quote_asset': quote_asset,
                    'status': 'Active',
                    'category': 'Spot'
                }
            )
            if created:
                self.stdout.write(f"  Created Symbol: {sym_name}")
            else:
                self.stdout.write(f"  Symbol exists: {sym_name}")

        # --- Relationships (ExchangeSymbolShip) ---
        # Define which exchanges should be linked to which symbols
        relationships_to_ensure = [
            {'exchange_name': 'binance', 'symbol_names': ['BTC/USDT', 'ETH/USDT']},
            {'exchange_name': 'huobi', 'symbol_names': ['BTC/USDT', 'ETH/USDT']},
            # {'exchange_name': 'binance', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
            # {'exchange_name': 'huobi', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
            # {'exchange_name': 'okx', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
            # {'exchange_name': 'bybit', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
            # {'exchange_name': 'bitget', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
            # {'exchange_name': 'bitmex', 'symbol_names': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']},
        ]
        self.stdout.write("\\n--- Seeding Relationships ---")
        for rel_data in relationships_to_ensure:
            try:
                exchange = Exchange.objects.get(name=rel_data['exchange_name'])
                for sym_name in rel_data['symbol_names']:
                    try:
                        # Use filter().first() to avoid DoesNotExist if symbol wasn't created above
                        symbol = Symbol.objects.filter(name=sym_name).first()
                        if not symbol:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Warning: Symbol '{sym_name}' not found for relationship with {exchange.name}. Skipping."))
                            continue

                        ship, created = ExchangeSymbolShip.objects.get_or_create(exchange=exchange, symbol=symbol)
                        if created:
                            self.stdout.write(f"  Created relationship: {exchange.name} <-> {symbol.name}")
                        else:
                            self.stdout.write(f"  Relationship exists: {exchange.name} <-> {symbol.name}")
                    except Exception as e:  # Catch potential errors during get_or_create
                        self.stdout.write(
                            self.style.ERROR(f"  Error creating relationship for {exchange.name} <-> {sym_name}: {e}"))
            except Exchange.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  Warning: Exchange '{rel_data['exchange_name']}' not found for relationship. Skipping."))

        self.stdout.write(self.style.SUCCESS('\\nSuccessfully finished basic exchange data initialization.'))
