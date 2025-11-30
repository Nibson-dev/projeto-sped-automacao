// app.js (COMPLETO E ATUALIZADO)
document.addEventListener("DOMContentLoaded", () => {
    // --- Seletores Padrão ---
    const fileSpedInput = document.getElementById("file_sped");
    const fileLivroInput = document.getElementById("file_livro");
    const manualModeCheckbox = document.getElementById("manual-mode-checkbox");
    const manualUploadArea = document.getElementById("manual-upload-area");
    const fileEntradasInput = document.getElementById("file_entradas_pdf");
    const fileSaidasInput = document.getElementById("file_saidas_pdf");
    const fileApuracaoInput = document.getElementById("file_apuracao_pdf");
    const btnProcessar = document.getElementById("btn-processar-tudo");
    const btnText = document.getElementById("btn-text-processar");
    const loader = document.getElementById("loader-processar");
    const statusGeral = document.getElementById("status-message-geral");
    const cardDetalhamento = document.getElementById("card-detalhamento");
    const statusDetalhamento = document.getElementById("status-detalhamento");
    const blocoETableBody = document.getElementById("bloco-e-table-body"); 
    const detalhamentoTableBody = document.getElementById("detalhamento-table-body");
    const cardAlertas = document.getElementById("card-alertas");
    const statusAlertas = document.getElementById("status-alertas");
    const listaAlertas = document.getElementById("lista-alertas-codigos");
    const cardDetalheE116 = document.getElementById("card-detalhe-e116");
    const statusDetalheE116 = document.getElementById("status-detalhe-e116");
    const spedE116Soma = document.getElementById("sped-e116-soma");
    const livroInfCompSoma = document.getElementById("livro-infcomp-soma");

    // --- [NOVO] Seletores para Extração Avançada ---
    const btnToggleAvancado = document.getElementById("btn-toggle-avancado");
    const cardExtracaoAvancada = document.getElementById("card-extracao-avancada");
    const statusExtracaoAvancada = document.getElementById("status-extracao-avancada");
    const tabelaAvancadaBody = document.getElementById("tabela-apuracao-avancada-body");
    
    // --- Listeners ---
    manualModeCheckbox.addEventListener("change", () => {
        manualUploadArea.classList.toggle("hidden", !manualModeCheckbox.checked);
    });

    // [NOVO] Listener para o botão de toggle do card avançado
    btnToggleAvancado.addEventListener("click", () => {
        const isHidden = cardExtracaoAvancada.classList.toggle("hidden");
        btnToggleAvancado.textContent = isHidden ? "Mostrar Extração Avançada (Apuração SPED)" : "Ocultar Extração Avançada";
    });

    // --- "Ouvinte" do Botão Mestre ---
    btnProcessar.addEventListener("click", async () => {
        limparResultados();
        const isManualMode = manualModeCheckbox.checked;
        let formData = new FormData();
        let endpoint = "";
        let statusInicial = "";

        // [NOVO] Coleta os campos avançados selecionados
        const advancedChecks = document.querySelectorAll(".chk-avancado:checked");
        const advancedFields = Array.from(advancedChecks).map(chk => chk.value);
        formData.append("advanced_fields_str", JSON.stringify(advancedFields));

        // Validação e preparação dos dados
        if (isManualMode) {
            if (!fileSpedInput.files[0] || !fileLivroInput.files[0] || !fileEntradasInput.files[0] || !fileSaidasInput.files[0] || !fileApuracaoInput.files[0]) {
                statusGeral.textContent = "ERRO: No modo manual, todos os 5 arquivos são obrigatórios.";
                return;
            }
            formData.append("file_sped", fileSpedInput.files[0]);
            formData.append("file_livro", fileLivroInput.files[0]);
            formData.append("file_entradas_pdf", fileEntradasInput.files[0]);
            formData.append("file_saidas_pdf", fileSaidasInput.files[0]);
            formData.append("file_apuracao_pdf", fileApuracaoInput.files[0]);
            endpoint = "/processar-manual/";
            statusInicial = "Iniciando análise manual (sem robô)... Isso deve ser rápido.";
        } else {
            if (!fileSpedInput.files[0] || !fileLivroInput.files[0]) {
                statusGeral.textContent = "ERRO: Você precisa selecionar o arquivo SPED.txt E o Livro.pdf.";
                return;
            }
            formData.append("file_sped", fileSpedInput.files[0]);
            formData.append("file_livro", fileLivroInput.files[0]);
            endpoint = "/upload-e-processar/";
            statusInicial = "Iniciando o robô (Wall-E)... Isso pode demorar vários minutos.";
        }
        
        statusGeral.textContent = statusInicial;
        btnProcessar.disabled = true;
        btnText.textContent = "Processando...";
        loader.classList.remove("hidden");

        try {
            const response = await fetch(endpoint, { method: "POST", body: formData });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Erro desconhecido no servidor.");
            }
            const resultados = await response.json();
            
            statusGeral.textContent = "Análise CONCLUÍDA! Verificando resultados...";
            
            // Preenche todos os cards padrão
            preencherBlocoE(resultados.bloco_e_texto); 
            preencherResultadosTotais(resultados); 
            preencherAlertasCodigos(resultados.codigos_ausentes_livro);
            preencherAnaliseDetalhamento(resultados.detalhamento_codigos);
            preencherConciliacaoDetalhes(resultados.conciliacao_detalhes);
            
            // [NOVO] Preenche o card de extração avançada
            preencherApuracaoAvancada(resultados.advanced_results);

            const soma_pdf_inf_comp = resultados.soma_livro_inf_comp || 0.0;
            const soma_sped_e116 = somarValoresE116(resultados.bloco_e_texto);
            preencherSomaE116(soma_sped_e116, soma_pdf_inf_comp);

        } catch (error) {
            console.error("Erro:", error);
            statusGeral.textContent = `ERRO: ${error.message}`;
            marcarCardsComoFalha();
        } finally {
            btnProcessar.disabled = false;
            btnText.textContent = "Processar Análise Completa";
            loader.classList.add("hidden");
        }
    });

    // --- FUNÇÕES DE PREENCHIMENTO ---
    
    function preencherBlocoE(textoBlocoE) {
        if (!blocoETableBody) return; 
        blocoETableBody.innerHTML = ""; 
        if (textoBlocoE && textoBlocoE !== "Bloco E não encontrado ou vazio.") {
            const linhas = textoBlocoE.split('\n');
            let htmlFinalTabela = ""; 
            const regexValor = /^\d[\d\.]*,\d{2}$/; 
            const regexCodigoAjuste = /^[A-Z]{2}\d{5,12}$/;
            
            linhas.forEach(linha => {
                if (!linha.trim()) return; 
                let classeLinha = ''; 
                if (linha.startsWith('|E110|')) classeLinha = 'reg-e110';
                else if (linha.startsWith('|E111|')) classeLinha = 'reg-e111';
                else if (linha.startsWith('|E116|')) classeLinha = 'reg-e116';
                else if (linha.startsWith('|E001|') || linha.startsWith('|E990|')) classeLinha = 'reg-e001';
                
                htmlFinalTabela += `<tr class="${classeLinha}">`;
                const campos = linha.split('|');
                
                for (let i = 1; i < campos.length - 1; i++) {
                    const campo = campos[i];
                    let classeCampo = 'campo-default'; 
                    let valorFormatado = campo;
                    
                    if (regexValor.test(campo)) {
                        classeCampo = 'valor-monetario';
                        valorFormatado = formatarNumero(campo); 
                    }
                    else if (regexCodigoAjuste.test(campo)) {
                        classeCampo = 'codigo-ajuste';
                    }
                    htmlFinalTabela += `<td class="${classeCampo}">${valorFormatado}</td>`;
                }
                htmlFinalTabela += `</tr>`;
            });
            blocoETableBody.innerHTML = htmlFinalTabela;
            statusDetalhamento.textContent = "Pronto para análise manual";
            cardDetalhamento.classList.add("ok");
        } else {
            blocoETableBody.innerHTML = '<tr><td class="status-divergente">ERRO: O Bloco E não pôde ser extraído do arquivo SPED.txt.</td></tr>';
            statusDetalhamento.textContent = "Falha ao ler Bloco E";
            cardDetalhamento.classList.add("divergente");
        }
    }
    
    // Esta é a sua lógica de SOMA (SUM)
    function preencherAnaliseDetalhamento(codigos) {
        if (!detalhamentoTableBody) return; 
        detalhamentoTableBody.innerHTML = ""; 
        if (codigos && Object.keys(codigos).length > 0) {
            detalhamentoTableBody.innerHTML = `
                <tr>
                    <th>Código de Ajuste</th>
                    <th>Valor Total no Livro (PDF)</th>
                </tr>
            `;
            Object.keys(codigos).sort().forEach(codigo => {
                const valorFormatado = formatarValorDecimal(codigos[codigo]);
                const row = `
                    <tr>
                        <td>${codigo}</td>
                        <td class="valor-monetario">R$ ${valorFormatado}</td>
                    </tr>
                `;
                detalhamentoTableBody.innerHTML += row;
            });
        } else {
            detalhamentoTableBody.innerHTML = `<tr><td colspan="2">Nenhum código de detalhamento (PA, MG, etc.) foi encontrado somado no Livro PDF.</td></tr>`;
            if(statusDetalhamento) statusDetalhamento.textContent = "Códigos não encontrados no PDF";
            if(cardDetalhamento) cardDetalhamento.classList.add("divergente");
        }
    }

    // Esta é a sua lógica de CAÇA (HUNT)
    function preencherConciliacaoDetalhes(detalhes) {
        // (Atualmente não temos uma tabela para isso, então apenas logamos)
        if (!detalhes || detalhes.length === 0) {
            console.log("Nenhum dado de 'conciliacao_detalhes' (HUNT) encontrado.");
            return;
        }
        console.log("Resultados da conciliação (HUNT):", detalhes);
    }
    
    function preencherResultadosTotais(data) {
        if (!data || !data.entradas) return;
        const { entradas, saidas, apuracao } = data;
        
        // Entradas
        const cardE = document.getElementById("card-entradas");
        cardE.classList.remove("aguardando");
        document.getElementById("sped-e-total").textContent = formatarNumero(entradas.sped?.total_operacao);
        document.getElementById("sped-e-bc").textContent = formatarNumero(entradas.sped?.base_de_calculo_icms);
        document.getElementById("sped-e-icms").textContent = formatarNumero(entradas.sped?.total_icms);
        document.getElementById("livro-e-total").textContent = formatarNumero(entradas.livro?.total_operacao);
        document.getElementById("livro-e-bc").textContent = formatarNumero(entradas.livro?.base_de_calculo_icms);
        document.getElementById("livro-e-icms").textContent = formatarNumero(entradas.livro?.total_icms);
        atualizarStatusCard("resultado-entradas", cardE, entradas.status, "Valores idênticos", "Valores divergentes");
        atualizarMiniStatus("status-e-total", entradas.status_detalhado?.total_operacao, "Total Op.");
        atualizarMiniStatus("status-e-bc", entradas.status_detalhado?.base_de_calculo_icms, "Base ICMS");
        atualizarMiniStatus("status-e-icms", entradas.status_detalhado?.total_icms, "Total ICMS");

        // Saídas
        const cardS = document.getElementById("card-saidas");
        cardS.classList.remove("aguardando");
        document.getElementById("sped-s-total").textContent = formatarNumero(saidas.sped?.total_operacao);
        document.getElementById("sped-s-bc").textContent = formatarNumero(saidas.sped?.base_de_calculo_icms);
        document.getElementById("sped-s-icms").textContent = formatarNumero(saidas.sped?.total_icms);
        document.getElementById("livro-s-total").textContent = formatarNumero(saidas.livro?.total_operacao);
        document.getElementById("livro-s-bc").textContent = formatarNumero(saidas.livro?.base_de_calculo_icms);
        document.getElementById("livro-s-icms").textContent = formatarNumero(saidas.livro?.total_icms);
        atualizarStatusCard("resultado-saidas", cardS, saidas.status, "Valores idênticos", "Valores divergentes");
        atualizarMiniStatus("status-s-total", saidas.status_detalhado?.total_operacao, "Total Op.");
        atualizarMiniStatus("status-s-bc", saidas.status_detalhado?.base_de_calculo_icms, "Base ICMS");
        atualizarMiniStatus("status-s-icms", saidas.status_detalhado?.total_icms, "Total ICMS");

        // Apuração Padrão
        const cardA = document.getElementById("card-apuracao");
        cardA.classList.remove("aguardando");
        document.getElementById("sped-a1").textContent = formatarNumero(apuracao.sped_recolher);
        document.getElementById("sped-a2").textContent = formatarNumero(apuracao.sped_saldo_credor);
        document.getElementById("livro-a1").textContent = formatarNumero(apuracao.livro_valores?.["013"]);
        document.getElementById("livro-a2").textContent = formatarNumero(apuracao.livro_valores?.["014"]);
        atualizarMiniStatus("resultado-apuracao-1", apuracao.status_recolher, "Cód. 013");
        atualizarMiniStatus("resultado-apuracao-2", apuracao.status_saldo_credor, "Cód. 014");
        if (apuracao.status_recolher === "OK" && apuracao.status_saldo_credor === "OK") {
            cardA.classList.add("ok");
        } else {
            cardA.classList.add("divergente");
        }
    }

    // [NOVA] Função para preencher a tabela de Extração Avançada
    function preencherApuracaoAvancada(resultadosAvancados) {
        if (!cardExtracaoAvancada || !tabelaAvancadaBody) return;
        
        tabelaAvancadaBody.innerHTML = ""; // Limpa a tabela
        cardExtracaoAvancada.classList.remove("aguardando");

        if (resultadosAvancados && resultadosAvancados.length > 0) {
            atualizarStatusCard("status-extracao-avancada", cardExtracaoAvancada, "OK", "Extração Concluída");
            
            resultadosAvancados.forEach(item => {
                const valorFormatado = formatarNumero(item.valor_sped);
                const statusClass = valorFormatado === "Não Encontrado" ? "status-atencao" : "valor-monetario";
                
                const row = `
                    <tr>
                        <td>${item.campo_nome}</td>
                        <td class="${statusClass}">${valorFormatado}</td>
                    </tr>
                `;
                tabelaAvancadaBody.innerHTML += row;
            });
        } else {
            // Se o usuário não selecionou nada, apenas marcamos como OK
            atualizarStatusCard("status-extracao-avancada", cardExtracaoAvancada, "OK", "Nenhum campo extra foi selecionado");
            tabelaAvancadaBody.innerHTML = '<tr><td colspan="2">Nenhum campo de extração avançada foi selecionado.</td></tr>';
        }
    }

    function preencherAlertasCodigos(codigos_ausentes) {
        cardAlertas.classList.remove("aguardando");
        listaAlertas.innerHTML = ""; 
        if (codigos_ausentes && codigos_ausentes.length > 0) {
            atualizarStatusCard("status-alertas", cardAlertas, "Divergente", null, `${codigos_ausentes.length} Alerta(s)`);
            codigos_ausentes.forEach(codigo => {
                listaAlertas.innerHTML += `<li>O código <b>${codigo}</b> (do SPED E111) não foi encontrado no Livro Fiscal.</li>`;
            });
        } else if (codigos_ausentes) { // Array vazio
            atualizarStatusCard("status-alertas", cardAlertas, "OK", "Tudo Certo");
            listaAlertas.innerHTML = "<li>Todos os códigos de ajuste E111 do SPED foram encontrados no Livro Fiscal.</li>";
        } else { // Nulo ou indefinido
            atualizarStatusCard("status-alertas", cardAlertas, "Divergente", null, "Falha na Verificação");
            listaAlertas.innerHTML = "<li>Não foi possível verificar os códigos E111.</li>";
        }
    }
    
    function preencherSomaE116(soma_sped, soma_pdf) {
        cardDetalheE116.classList.remove("aguardando");
        spedE116Soma.textContent = `R$ ${formatarValorDecimal(soma_sped)}`;
        livroInfCompSoma.textContent = `R$ ${formatarValorDecimal(soma_pdf)}`;
        const status = Math.abs(soma_sped - soma_pdf) < 0.01 ? "OK" : "Divergente";
        atualizarStatusCard("status-detalhe-e116", cardDetalheE116, status, "Valores idênticos", "Valores divergentes");
    }

    // --- FUNÇÕES AUXILIARES E DE LIMPEZA ---
    function formatarNumero(numStr) {
        if (!numStr || typeof numStr !== 'string' || numStr.includes("ERRO") || numStr.includes("Não lido")) return numStr || "--";
        if (numStr.match(/^\d[\d\.]*,\d{2}$/)) {
             let valor = parseFloat(numStr.replace(/\./g, "").replace(",", "."));
             if (isNaN(valor)) return numStr;
             return 'R$ ' + valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        return numStr;
    }

    function formatarValorDecimal(num) {
        const valor = parseFloat(num);
        if (isNaN(valor)) return "--";
        return valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function somarValoresE116(blocoETexto) {
        if (!blocoETexto || typeof blocoETexto !== 'string') return 0.0;
        return blocoETexto.split('\n').reduce((total, linha) => {
            if (linha.startsWith('|E116|')) {
                const campos = linha.split('|');
                if (campos.length > 3) {
                    const valorLimpo = campos[3].replace(/\./g, "").replace(",", ".");
                    const valorFloat = parseFloat(valorLimpo);
                    if (!isNaN(valorFloat)) return total + valorFloat;
                }
            }
            return total;
        }, 0.0);
    }

    function atualizarStatusCard(elementId, cardElement, status, okText, divText) {
        const el = document.getElementById(elementId);
        cardElement.classList.remove("ok", "divergente");
        if (status === "OK") {
            el.textContent = okText;
            el.className = "status-box ok";
            cardElement.classList.add("ok");
        } else {
            el.textContent = divText;
            el.className = "status-box divergente";
            cardElement.classList.add("divergente");
        }
    }

    function atualizarMiniStatus(elementId, status, nome) {
        const el = document.getElementById(elementId);
        el.classList.remove("aguardando", "ok", "divergente");
        if (status === "OK") {
            el.textContent = `${nome} OK`;
            el.classList.add("ok");
        } else {
            el.textContent = `${nome} Divergente`;
            el.classList.add("divergente");
        }
    }
    
    function limparResultados() {
        document.querySelectorAll('.card-resultado').forEach(card => {
            card.className = card.className.replace(/ok|divergente/g, 'aguardando').replace(/\s*aguardando\s*/g, ' ') + ' aguardando';
        });
        document.querySelectorAll('.status-box, .status-box-mini').forEach(box => {
            box.textContent = "Aguardando...";
            box.className = box.className.replace(/ok|divergente/g, 'aguardando');
        });
        document.querySelectorAll('span[id^="sped-"], span[id^="livro-"]').forEach(span => {
            span.textContent = "--";
        });
        statusGeral.textContent = "";
        listaAlertas.innerHTML = "";
        detalhamentoTableBody.innerHTML = "";
        blocoETableBody.innerHTML = "";
        
        // [NOVO] Limpa e esconde o card avançado
        if(cardExtracaoAvancada) {
            cardExtracaoAvancada.classList.add("hidden");
            cardExtracaoAvancada.classList.remove("ok", "divergente");
            cardExtracaoAvancada.classList.add("aguardando");
        }
        if(tabelaAvancadaBody) tabelaAvancadaBody.innerHTML = "";
        if(statusExtracaoAvancada) {
            statusExtracaoAvancada.textContent = "Aguardando...";
            statusExtracaoAvancada.className = "status-box aguardando";
        }
        if(btnToggleAvancado) btnToggleAvancado.textContent = "Mostrar Extração Avançada (Apuração SPED)";
    }

    function marcarCardsComoFalha() {
         document.querySelectorAll('.card-resultado').forEach(card => {
            card.classList.remove('aguardando', 'ok');
            card.classList.add('divergente');
        });
         document.querySelectorAll('.status-box, .status-box-mini').forEach(box => {
            box.textContent = "Falha";
            box.className = box.className.replace(/aguardando|ok/g, 'divergente');
        });
    }
    
    // --- Filtros e Menu ---
    const filtroBtns = document.querySelectorAll(".filtro-btn");
    filtroBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            filtroBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            const filtro = btn.dataset.filtro; 
            const linhas = blocoETableBody.querySelectorAll("tr");
            linhas.forEach(linha => {
                if (filtro === "todos" || linha.classList.contains(filtro)) {
                    linha.style.display = ""; 
                } else {
                    linha.style.display = "none"; 
                }
            });
        });
    });
});