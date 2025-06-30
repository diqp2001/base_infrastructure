"""
Genetic Algorithm Optimizer implementation.
Provides genetic algorithm optimization with selection, crossover, and mutation strategies.
"""

import random
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable, Dict, Any
from datetime import datetime
import numpy as np

from .interfaces import IOptimizer, IOptimizationTarget, ISelectionStrategy, ICrossoverStrategy, IMutationStrategy
from .parameter_management import OptimizationParameterSet, ParameterSpace
from .result_management import OptimizationResult, OptimizationStatistics
from .configuration import OptimizerConfiguration
from .enums import SelectionType, CrossoverType, MutationType, OptimizationStatus


@dataclass
class Individual:
    """
    Represents a single solution (individual) in the genetic algorithm.
    Contains genes (parameter values), fitness, and genealogy information.
    """
    parameter_set: OptimizationParameterSet
    fitness: Optional[float] = None
    age: int = 0
    generation: int = 0
    rank: Optional[int] = None
    crowding_distance: float = 0.0
    
    def __post_init__(self):
        """Update fitness from parameter set if available."""
        if self.fitness is None and self.parameter_set.fitness is not None:
            self.fitness = self.parameter_set.fitness
    
    def is_evaluated(self) -> bool:
        """Check if individual has been evaluated (has fitness)."""
        return self.fitness is not None
    
    def copy(self) -> 'Individual':
        """Create a copy of the individual with new unique ID."""
        return Individual(
            parameter_set=self.parameter_set.copy(),
            fitness=self.fitness,
            age=self.age,
            generation=self.generation,
            rank=self.rank,
            crowding_distance=self.crowding_distance
        )
    
    def mutate_parameter(self, parameter_name: str, new_value: Any) -> None:
        """Mutate a specific parameter value."""
        self.parameter_set.set_parameter_value(parameter_name, new_value)
        # Reset fitness as individual has changed
        self.fitness = None
        self.parameter_set.fitness = None
    
    def __lt__(self, other: 'Individual') -> bool:
        """Less than comparison based on fitness (for sorting)."""
        if self.fitness is None:
            return True
        if other.fitness is None:
            return False
        return self.fitness < other.fitness
    
    def __repr__(self) -> str:
        """String representation of individual."""
        return f"Individual(fitness={self.fitness}, gen={self.generation}, age={self.age})"


class Population:
    """
    Collection of individuals in the genetic algorithm.
    Manages population operations like initialization, selection, and replacement.
    """
    
    def __init__(self, size: int, parameter_space: ParameterSpace):
        self.size = size
        self.parameter_space = parameter_space
        self.individuals: List[Individual] = []
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.worst_individual: Optional[Individual] = None
        self.average_fitness: float = 0.0
    
    def initialize_random(self) -> None:
        """Initialize population with random individuals."""
        self.individuals = []
        for _ in range(self.size):
            param_set = self.parameter_space.generate_random_parameter_set()
            param_set.generation = self.generation
            individual = Individual(parameter_set=param_set, generation=self.generation)
            self.individuals.append(individual)
    
    def add_individual(self, individual: Individual) -> None:
        """Add an individual to the population."""
        individual.generation = self.generation
        self.individuals.append(individual)
    
    def remove_individual(self, individual: Individual) -> bool:
        """Remove an individual from the population."""
        if individual in self.individuals:
            self.individuals.remove(individual)
            return True
        return False
    
    def update_statistics(self) -> None:
        """Update population statistics."""
        if not self.individuals:
            return
        
        evaluated_individuals = [ind for ind in self.individuals if ind.is_evaluated()]
        if not evaluated_individuals:
            return
        
        fitnesses = [ind.fitness for ind in evaluated_individuals]
        self.average_fitness = np.mean(fitnesses)
        
        self.best_individual = max(evaluated_individuals, key=lambda x: x.fitness)
        self.worst_individual = min(evaluated_individuals, key=lambda x: x.fitness)
    
    def get_best_individuals(self, n: int) -> List[Individual]:
        """Get the n best individuals in the population."""
        evaluated_individuals = [ind for ind in self.individuals if ind.is_evaluated()]
        return sorted(evaluated_individuals, key=lambda x: x.fitness, reverse=True)[:n]
    
    def get_worst_individuals(self, n: int) -> List[Individual]:
        """Get the n worst individuals in the population."""
        evaluated_individuals = [ind for ind in self.individuals if ind.is_evaluated()]
        return sorted(evaluated_individuals, key=lambda x: x.fitness)[:n]
    
    def replace_worst(self, new_individuals: List[Individual]) -> None:
        """Replace worst individuals with new individuals."""
        if not new_individuals:
            return
        
        worst_individuals = self.get_worst_individuals(len(new_individuals))
        for old_ind, new_ind in zip(worst_individuals, new_individuals):
            self.remove_individual(old_ind)
            self.add_individual(new_ind)
    
    def age_population(self) -> None:
        """Increment age of all individuals."""
        for individual in self.individuals:
            individual.age += 1
    
    def next_generation(self) -> None:
        """Move to the next generation."""
        self.generation += 1
        self.age_population()
    
    def get_diversity(self) -> float:
        """Calculate population diversity based on parameter variance."""
        if len(self.individuals) < 2:
            return 0.0
        
        parameter_names = self.parameter_space.get_parameter_names()
        if not parameter_names:
            return 0.0
        
        total_variance = 0.0
        valid_parameters = 0
        
        for param_name in parameter_names:
            values = []
            for individual in self.individuals:
                value = individual.parameter_set.get_parameter_value(param_name)
                if isinstance(value, (int, float)):
                    values.append(float(value))
            
            if len(values) > 1:
                total_variance += np.var(values)
                valid_parameters += 1
        
        return total_variance / valid_parameters if valid_parameters > 0 else 0.0
    
    def __len__(self) -> int:
        """Get population size."""
        return len(self.individuals)
    
    def __iter__(self):
        """Iterate over individuals."""
        return iter(self.individuals)
    
    def __repr__(self) -> str:
        """String representation of population."""
        return f"Population(size={len(self.individuals)}, gen={self.generation}, best_fitness={self.best_individual.fitness if self.best_individual else 'N/A'})"


class TournamentSelection(ISelectionStrategy):
    """Tournament selection strategy for genetic algorithm."""
    
    def __init__(self, tournament_size: int = 3, selection_pressure: float = 2.0):
        self.tournament_size = tournament_size
        self.selection_pressure = selection_pressure
    
    def select_parents(self, population: Population, num_parents: int) -> List[Individual]:
        """Select parents using tournament selection."""
        parents = []
        evaluated_individuals = [ind for ind in population.individuals if ind.is_evaluated()]
        
        if not evaluated_individuals:
            return []
        
        for _ in range(num_parents):
            # Select tournament participants
            tournament = random.sample(evaluated_individuals, 
                                     min(self.tournament_size, len(evaluated_individuals)))
            
            # Apply selection pressure
            tournament.sort(key=lambda x: x.fitness, reverse=True)
            
            # Select winner with probability based on selection pressure
            for i, individual in enumerate(tournament):
                probability = (self.selection_pressure - 1) ** i / sum(
                    (self.selection_pressure - 1) ** j for j in range(len(tournament))
                )
                if random.random() < probability:
                    parents.append(individual)
                    break
            else:
                # Fallback to best in tournament
                parents.append(tournament[0])
        
        return parents


class RouletteWheelSelection(ISelectionStrategy):
    """Roulette wheel (fitness proportionate) selection strategy."""
    
    def select_parents(self, population: Population, num_parents: int) -> List[Individual]:
        """Select parents using roulette wheel selection."""
        parents = []
        evaluated_individuals = [ind for ind in population.individuals if ind.is_evaluated()]
        
        if not evaluated_individuals:
            return []
        
        # Handle negative fitness values by shifting
        fitnesses = [ind.fitness for ind in evaluated_individuals]
        min_fitness = min(fitnesses)
        if min_fitness < 0:
            adjusted_fitnesses = [f - min_fitness + 1 for f in fitnesses]
        else:
            adjusted_fitnesses = fitnesses
        
        total_fitness = sum(adjusted_fitnesses)
        if total_fitness == 0:
            # All individuals have zero fitness, select randomly
            return random.choices(evaluated_individuals, k=num_parents)
        
        # Calculate selection probabilities
        probabilities = [f / total_fitness for f in adjusted_fitnesses]
        
        for _ in range(num_parents):
            parent = np.random.choice(evaluated_individuals, p=probabilities)
            parents.append(parent)
        
        return parents


class UniformCrossover(ICrossoverStrategy):
    """Uniform crossover strategy for genetic algorithm."""
    
    def __init__(self, crossover_probability: float = 0.5):
        self.crossover_probability = crossover_probability
    
    def crossover(self, parent1: Individual, parent2: Individual) -> List[Individual]:
        """Perform uniform crossover between two parents."""
        child1_params = {}
        child2_params = {}
        
        # Get all parameter names
        all_params = set(parent1.parameter_set.parameters.keys()) | set(parent2.parameter_set.parameters.keys())
        
        for param_name in all_params:
            value1 = parent1.parameter_set.get_parameter_value(param_name)
            value2 = parent2.parameter_set.get_parameter_value(param_name)
            
            # Uniform crossover: randomly choose which parent contributes each gene
            if random.random() < self.crossover_probability:
                child1_params[param_name] = value2
                child2_params[param_name] = value1
            else:
                child1_params[param_name] = value1
                child2_params[param_name] = value2
        
        # Create offspring
        child1_param_set = OptimizationParameterSet(
            parameters=child1_params,
            parent_ids=[parent1.parameter_set.unique_id, parent2.parameter_set.unique_id]
        )
        child2_param_set = OptimizationParameterSet(
            parameters=child2_params,
            parent_ids=[parent1.parameter_set.unique_id, parent2.parameter_set.unique_id]
        )
        
        child1 = Individual(parameter_set=child1_param_set)
        child2 = Individual(parameter_set=child2_param_set)
        
        return [child1, child2]


class GaussianMutation(IMutationStrategy):
    """Gaussian mutation strategy for genetic algorithm."""
    
    def __init__(self, mutation_sigma: float = 0.1):
        self.mutation_sigma = mutation_sigma
    
    def mutate(self, individual: Individual, mutation_rate: float) -> Individual:
        """Apply Gaussian mutation to an individual."""
        mutated_individual = individual.copy()
        
        for param_name, param_value in mutated_individual.parameter_set.parameters.items():
            if random.random() < mutation_rate:
                # Apply Gaussian mutation based on parameter type
                if isinstance(param_value, (int, float)):
                    # Add Gaussian noise
                    noise = np.random.normal(0, self.mutation_sigma * abs(param_value) if param_value != 0 else self.mutation_sigma)
                    new_value = param_value + noise
                    
                    # Ensure value is within parameter bounds
                    parameter = mutated_individual.parameter_set.parameters.get(param_name)
                    if parameter:
                        # Get parameter definition from parameter space if available
                        # For now, just apply the mutation
                        mutated_individual.mutate_parameter(param_name, new_value)
                    else:
                        mutated_individual.mutate_parameter(param_name, new_value)
                
                # For non-numeric parameters, we might implement different mutation strategies
                # This is a simplified version
        
        return mutated_individual


class GeneticOptimizer(IOptimizer):
    """
    Genetic Algorithm optimizer implementation.
    Implements the complete genetic algorithm with configurable strategies.
    """
    
    def __init__(self, 
                 parameter_space: ParameterSpace,
                 target_function: IOptimizationTarget,
                 configuration: Optional[OptimizerConfiguration] = None):
        self.parameter_space = parameter_space
        self.target_function = target_function
        self.configuration = configuration or OptimizerConfiguration()
        
        # Population
        self.population: Optional[Population] = None
        
        # Strategies
        self.selection_strategy = self._create_selection_strategy()
        self.crossover_strategy = self._create_crossover_strategy()
        self.mutation_strategy = self._create_mutation_strategy()
        
        # State
        self.current_generation = 0
        self.is_running = False
        self.is_stopped = False
        self.best_result: Optional[OptimizationResult] = None
        self.all_results: List[OptimizationResult] = []
        
        # Statistics
        self.statistics = OptimizationStatistics(
            optimization_id=self.configuration.optimization_id,
            start_time=datetime.now()
        )
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    def _create_selection_strategy(self) -> ISelectionStrategy:
        """Create selection strategy based on configuration."""
        if self.configuration.selection_type == SelectionType.TOURNAMENT:
            return TournamentSelection(
                tournament_size=self.configuration.tournament_size,
                selection_pressure=self.configuration.selection_pressure
            )
        elif self.configuration.selection_type == SelectionType.ROULETTE_WHEEL:
            return RouletteWheelSelection()
        else:
            # Default to tournament selection
            return TournamentSelection()
    
    def _create_crossover_strategy(self) -> ICrossoverStrategy:
        """Create crossover strategy based on configuration."""
        if self.configuration.crossover_type == CrossoverType.UNIFORM:
            return UniformCrossover(crossover_probability=0.5)
        else:
            # Default to uniform crossover
            return UniformCrossover()
    
    def _create_mutation_strategy(self) -> IMutationStrategy:
        """Create mutation strategy based on configuration."""
        if self.configuration.mutation_type == MutationType.GAUSSIAN:
            return GaussianMutation(mutation_sigma=self.configuration.mutation_sigma)
        else:
            # Default to Gaussian mutation
            return GaussianMutation()
    
    def initialize(self, configuration: OptimizerConfiguration) -> None:
        """Initialize the optimizer with configuration settings."""
        self.configuration = configuration
        
        # Recreate strategies with new configuration
        self.selection_strategy = self._create_selection_strategy()
        self.crossover_strategy = self._create_crossover_strategy()
        self.mutation_strategy = self._create_mutation_strategy()
        
        # Reset state
        self.current_generation = 0
        self.is_running = False
        self.is_stopped = False
        self.best_result = None
        self.all_results = []
        
        # Initialize population
        self.population = Population(self.configuration.population_size, self.parameter_space)
        self.population.initialize_random()
        
        self.logger.info(f"Genetic optimizer initialized with population size {self.configuration.population_size}")
    
    async def optimize(self) -> OptimizationStatistics:
        """Run the genetic algorithm optimization process."""
        if not self.population:
            self.initialize(self.configuration)
        
        self.is_running = True
        self.statistics.start_time = datetime.now()
        
        try:
            # Evaluate initial population
            await self._evaluate_population(self.population)
            self.population.update_statistics()
            
            # Main evolution loop
            for generation in range(self.configuration.max_generations):
                if self.is_stopped:
                    break
                
                self.current_generation = generation
                self.logger.info(f"Starting generation {generation}")
                
                # Create next generation
                new_population = await self._create_next_generation(self.population)
                
                # Evaluate new population
                await self._evaluate_population(new_population)
                new_population.update_statistics()
                
                # Apply elitism and replacement
                self._apply_elitism(self.population, new_population)
                
                # Update population
                self.population = new_population
                self.population.next_generation()
                
                # Update statistics
                self.statistics.generations_completed = generation + 1
                
                # Check convergence
                if self._check_convergence():
                    self.logger.info(f"Convergence achieved at generation {generation}")
                    self.statistics.convergence_achieved = True
                    self.statistics.convergence_generation = generation
                    break
                
                # Report progress
                if generation % self.configuration.progress_reporting_interval == 0:
                    self._report_progress(generation)
            
            # Finalize statistics
            self.statistics.end_time = datetime.now()
            self.statistics.update_with_results(self.all_results)
            
            self.logger.info(f"Genetic algorithm completed. Best fitness: {self.best_result.fitness if self.best_result else 'N/A'}")
            
        except Exception as e:
            self.logger.error(f"Error during genetic algorithm optimization: {e}")
            raise
        finally:
            self.is_running = False
        
        return self.statistics
    
    async def _evaluate_population(self, population: Population) -> None:
        """Evaluate all unevaluated individuals in the population."""
        unevaluated_individuals = [ind for ind in population.individuals if not ind.is_evaluated()]
        
        if not unevaluated_individuals:
            return
        
        # Create semaphore for concurrent evaluation
        semaphore = asyncio.Semaphore(self.configuration.max_concurrent_backtests)
        
        async def evaluate_individual(individual: Individual) -> None:
            async with semaphore:
                try:
                    result = await self.target_function.evaluate(individual.parameter_set)
                    individual.fitness = result.fitness
                    individual.parameter_set.fitness = result.fitness
                    
                    self.all_results.append(result)
                    
                    # Update best result
                    if self.best_result is None or result.fitness > self.best_result.fitness:
                        self.best_result = result
                    
                except Exception as e:
                    self.logger.error(f"Error evaluating individual: {e}")
                    individual.fitness = float('-inf')  # Assign worst fitness
        
        # Evaluate all individuals concurrently
        tasks = [evaluate_individual(individual) for individual in unevaluated_individuals]
        await asyncio.gather(*tasks)
    
    async def _create_next_generation(self, current_population: Population) -> Population:
        """Create the next generation through selection, crossover, and mutation."""
        new_population = Population(self.configuration.population_size, self.parameter_space)
        
        # Calculate number of offspring to create
        num_elite = int(self.configuration.elitism_rate * self.configuration.population_size)
        num_offspring = self.configuration.population_size - num_elite
        
        # Generate offspring through crossover and mutation
        offspring = []
        while len(offspring) < num_offspring:
            # Select parents
            parents = self.selection_strategy.select_parents(current_population, 2)
            if len(parents) < 2:
                break
            
            # Crossover
            if random.random() < self.configuration.crossover_rate:
                children = self.crossover_strategy.crossover(parents[0], parents[1])
            else:
                # Copy parents if no crossover
                children = [parents[0].copy(), parents[1].copy()]
            
            # Mutation
            for child in children:
                if random.random() < self.configuration.mutation_rate:
                    mutated_child = self.mutation_strategy.mutate(child, self.configuration.mutation_rate)
                    offspring.append(mutated_child)
                else:
                    offspring.append(child)
        
        # Add offspring to new population
        for individual in offspring[:num_offspring]:
            new_population.add_individual(individual)
        
        return new_population
    
    def _apply_elitism(self, old_population: Population, new_population: Population) -> None:
        """Apply elitism by preserving best individuals from previous generation."""
        num_elite = int(self.configuration.elitism_rate * self.configuration.population_size)
        if num_elite == 0:
            return
        
        # Get best individuals from old population
        elite_individuals = old_population.get_best_individuals(num_elite)
        
        # Replace worst individuals in new population
        worst_individuals = new_population.get_worst_individuals(len(elite_individuals))
        
        for worst_ind in worst_individuals:
            new_population.remove_individual(worst_ind)
        
        for elite_ind in elite_individuals:
            elite_copy = elite_ind.copy()
            new_population.add_individual(elite_copy)
    
    def _check_convergence(self) -> bool:
        """Check if the algorithm has converged."""
        if not self.best_result:
            return False
        
        # Check if target fitness is reached
        if (self.configuration.target_fitness is not None and 
            self.best_result.fitness >= self.configuration.target_fitness):
            return True
        
        # Check for fitness improvement over recent generations
        if len(self.all_results) >= self.configuration.convergence_generations:
            recent_results = self.all_results[-self.configuration.convergence_generations:]
            recent_best_fitness = max(result.fitness for result in recent_results)
            
            if self.best_result.fitness - recent_best_fitness < self.configuration.convergence_threshold:
                return True
        
        return False
    
    def _report_progress(self, generation: int) -> None:
        """Report optimization progress."""
        if self.population and self.population.best_individual:
            best_fitness = self.population.best_individual.fitness
            avg_fitness = self.population.average_fitness
            diversity = self.population.get_diversity()
            
            self.logger.info(
                f"Generation {generation}: "
                f"Best fitness: {best_fitness:.6f}, "
                f"Avg fitness: {avg_fitness:.6f}, "
                f"Diversity: {diversity:.6f}"
            )
    
    def get_next_parameter_set(self) -> Optional[OptimizationParameterSet]:
        """Get the next parameter set to evaluate."""
        # For genetic algorithm, this is handled internally
        # This method is more relevant for grid search
        return None
    
    def register_result(self, result: OptimizationResult) -> None:
        """Register the result of evaluating a parameter set."""
        self.all_results.append(result)
        
        # Update best result
        if self.best_result is None or result.fitness > self.best_result.fitness:
            self.best_result = result
    
    def is_complete(self) -> bool:
        """Check if the optimization process is complete."""
        return (self.current_generation >= self.configuration.max_generations or 
                self.statistics.convergence_achieved or
                self.is_stopped)
    
    def get_best_result(self) -> Optional[OptimizationResult]:
        """Get the best result found so far."""
        return self.best_result
    
    def get_progress(self) -> float:
        """Get optimization progress as a percentage (0.0 to 1.0)."""
        if self.configuration.max_generations == 0:
            return 0.0
        return min(1.0, self.current_generation / self.configuration.max_generations)
    
    def stop(self) -> None:
        """Stop the optimization process."""
        self.is_stopped = True
        self.logger.info("Genetic algorithm optimization stopped")
    
    def __repr__(self) -> str:
        """String representation of the genetic optimizer."""
        return (f"GeneticOptimizer(population_size={self.configuration.population_size}, "
                f"generation={self.current_generation}, "
                f"best_fitness={self.best_result.fitness if self.best_result else 'N/A'})")