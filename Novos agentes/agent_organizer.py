import pandas as pd
import xmltodict
import os

class OrganizerAgent:
    def process_data(self, files, logger_func=print):
        """
        Reads content from files (XML/Excel) and organizes them into a DataFrame.
        Expected keys in 'files': 'id' (path or drive_id), 'name', 'mimeType', 'local_path' (optional)
        """
        def log(msg):
            logger_func(msg)

        log("Organizer Agent: Processing data...")
        
        extracted_data = []

        for file_info in files:
            # Determine path: use 'local_path' if downloaded/local, else 'id' if it looks like a path
            file_path = file_info.get("local_path", file_info.get("id"))
            
            # If still just an ID (Drive) and no local_path, we can't read it here yet
            # (Main should have handled download)
            if not os.path.exists(file_path):
                log(f"Skipping {file_info['name']}: File not found locally.")
                continue

            try:
                data = None
                if file_path.lower().endswith('.xml'):
                    data = self._parse_xml(file_path)
                elif file_path.lower().endswith(('.xlsx', '.xls')):
                    data = self._parse_excel(file_path)
                elif file_path.lower().endswith('.csv'):
                    data = self._parse_csv(file_path)
                else:
                    # Fallback or Skip
                    # log(f"Skipping {file_info['name']}: Unsupported format.")
                    continue
                
                if data:
                    data['Nome Arquivo'] = file_info['name']
                    extracted_data.append(data)

            except Exception as e:
                log(f"Error processing {file_info['name']}: {e}")

        df = pd.DataFrame(extracted_data)
        
        # Ensure columns exist even if empty
        expected_cols = ['Nome Arquivo', 'Faturamento', 'Impostos (Total)', 'Aliquota', 'Base Calculo', 'Retencoes', 'Valor Liquido']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0.0

        # Reorder to match user request
        df = df[expected_cols]
        
        # Clean/Fill NaNs
        df = df.fillna(0)

        log(f"Organizer Agent: Processed {len(df)} records.")
        return df

    def _parse_number(self, val_str):
        """Converts PT-BR number string (1.234,56) to float (1234.56)."""
        if isinstance(val_str, (int, float)):
            return float(val_str)
        try:
            # Remove dots, replace comma with dot
            clean_str = str(val_str).replace('.', '').replace(',', '.')
            return float(clean_str)
        except:
            return 0.0

    def _parse_xml(self, file_path):
        """Parses NFe XML to extract tax info."""
        try:
            with open(file_path, 'rb') as f:
                doc = xmltodict.parse(f)
            
            # Navigate the potentially complex NFe structure. 
            # Structure varies (NFe vs NFCe vs NFS-e), this is a generic attempt for NFe.
            # Ideally, we look for key tags recursively or use known paths.
            
            # Simplified access attempting to find 'infNFe'
            
            # Try standard NFe path
            nfe = doc.get('nfeProc', {}).get('NFe', {}).get('infNFe', {})
            if not nfe:
                nfe = doc.get('NFe', {}).get('infNFe', {})
            
            total = nfe.get('total', {}).get('ICMSTot', {})
            
            # Extract Values (converting to float)
            def get_val(obj, key):
                return float(obj.get(key, 0))

            faturamento = get_val(total, 'vNF')
            impostos = get_val(total, 'vTotTrib') # Or sum of vICMS, vIPI, vPIS, vCOFINS
            if impostos == 0:
                 # Calculate manually if vTotTrib is empty
                 impostos = get_val(total, 'vICMS') + get_val(total, 'vIPI') + get_val(total, 'vPIS') + get_val(total, 'vCOFINS')

            base_calc = get_val(total, 'vBC')
            
            # Retentions often in 'retTrib' or separate
            # For this MVP, let's look for standard fields
            retencoes = 0.0 # Placeholder
            
            valor_liq = faturamento - retencoes # Simplified logic

            return {
                'Faturamento': faturamento,
                'Impostos (Total)': impostos,
                'Aliquota': 0.0, # Hard to infer single rate for whole NFe
                'Base Calculo': base_calc,
                'Retencoes': retencoes,
                'Valor Liquido': valor_liq
            }
        except Exception as e:
            # print(f"XML Parse Error: {e}")
            return None

    def _parse_excel(self, file_path):
        """Parses Excel to find Billing/Tax columns."""
        # Heuristic: Read first sheet, look for header row
        try:
            df = pd.read_excel(file_path)
            
            # Normalize columns to lowercase for search
            df.columns = df.columns.astype(str).str.lower()
            
            # Look for keywords
            faturamento = 0.0
            impostos = 0.0
            
            # Simple sum of columns that look like 'valor' or 'total'
            for col in df.columns:
                if 'total' in col or 'valor' in col:
                    faturamento = df[col].sum()
                    break # Take first match
            
            for col in df.columns:
                if 'imposto' in col or 'tributo' in col:
                    impostos = df[col].sum()
                    break

            return {
                'Faturamento': faturamento,
                'Impostos (Total)': impostos,
                'Aliquota': 0.0,
                'Base Calculo': faturamento, # Assumption
                'Retencoes': 0.0,
                'Valor Liquido': faturamento - impostos
            }
        except Exception:
            return None

    def _parse_csv(self, file_path):
        """Parses CSV (unstructured) to find Billing/Tax info."""
        try:
            # Read as text lines because it might not be a clean table
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            faturamento = 0.0
            impostos = 0.0
            base_calc = 0.0
            retencoes = 0.0
            aliquota = 0.0

            for line in lines:
                line_lower = line.lower()
                parts = line.split(';')
                
                # Check for Base de Calculo / Total
                if 'total' in line_lower and 'serviços' not in line_lower: # Avoid "Total Serviços" duplications if listed twice
                     # Look for the numeric part
                     for part in parts:
                         val = self._parse_number(part)
                         if val > 0:
                             # Heuristic: largest "Total" found could be Faturamento/Base
                             if val > faturamento:
                                 faturamento = val
                                 base_calc = val

                # Check for Taxes
                if 'valor final do imposto' in line_lower or 'imposto a recolher' in line_lower:
                    for part in parts:
                        val = self._parse_number(part)
                        if val > 0:
                            impostos = val
                
                # Check for Aliquota
                if 'alíquota' in line_lower or '%' in line:
                     for part in parts:
                         val = self._parse_number(part)
                         if val > 0:
                             # This catches the calculated tax amount from the line "Aliquota X%; Value"
                             # In the example CSV: "Alíquota 3,00%;1.029,92"
                             # If we haven't found a "Final Tax", this is a good candidate
                             if impostos == 0:
                                 impostos = val

                # Check for Retentions
                if 'valor retido' in line_lower:
                    for part in parts:
                        val = self._parse_number(part)
                        if val > 0:
                            retencoes = val

            return {
                'Faturamento': faturamento,
                'Impostos (Total)': impostos,
                'Aliquota': 0.0, # Hard to parse exact rate from text easily without regex
                'Base Calculo': base_calc,
                'Retencoes': retencoes,
                'Valor Liquido': faturamento - impostos - retencoes
            }
        except Exception as e:
            print(f"CSV Parse Error: {e}")
            return None
