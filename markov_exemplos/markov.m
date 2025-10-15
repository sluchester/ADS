pkg load queueing

# P = [0.6 0.4; 0.4 0.6];

# p = dtmc(P);
# disp(p);

# # após 3 passos
# p = dtmc(P,3, [1 0]);
# disp(p);

# conjunto de probabilidades setadas no código markov_chain.py
# matriz de probabilidade de transição em um estado
stochastic_matrix = [0.7,0.2,0.1;0.3,0.4,0.3;0.2,0.3,0.5];
p = dtmc(stochastic_matrix);
disp("Distribuição estacionária π para o IPERF_MARKOV: ");
disp(p);


# Atividade AE2.2 - Canal de Comunicação com 3 Estados
P_matrix = [0.7 0.2 0.1; 0.3 0.4 0.3; 0.2 0.3 0.5];

# Determine a distribuição estacionária π = (π1, π2, π3)
pi_stacionary = dtmc(P_matrix);
disp("Distribuição estacionária π: ");
disp(pi_stacionary);

pi_2_states = dtmc(P_matrix, 2, [1 0 0]);
disp("Distribuição após 2 passos: ");
disp(pi_2_states);

P_1_2_1 = P_matrix(1,2) * P_matrix(2,1);
P_1_3_1 = P_matrix(1,3) * P_matrix(3,1);
disp("Probabilidade de retornar ao estado 1 passando por 2: ");
disp(P_1_2_1);
disp("Probabilidade de retornar ao estado 1 passando por 3: ");
disp(P_1_3_1);